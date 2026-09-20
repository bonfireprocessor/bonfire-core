"""
Simple 3 Stage Pipeline for bonfire_core 
(c) 2019-2026 The Bonfire Project
License: See LICENSE
"""


from myhdl import *

from rtl.decode import *
from rtl.execute import *
from rtl.regfile import * 
from rtl.debug.abstract_command import (
    AbstractCommandController,
    AbstractRegisterTransferBundle,
    ProgbufCompletionBundle,
    ProgbufIssueBundle,
)
from rtl.debug.hart_debug import HartDebugController
from rtl.debug.pipeline_adapter import (
    DebugPipelineAdapter,
    DebugPipelineEventBundle,
    DebugPipelineRequestBundle,
)
from rtl.pipeline_events import (
    PIPELINE_SOURCE_NORMAL,
    PIPELINE_SOURCE_PROGRAM_BUFFER,
    PipelineBoundaryEventBundle,
)

from  rtl import config
def_config= config.BonfireConfig()

class FetchInputBundle:
     def __init__(self,config=def_config):
        self.config=config
        xlen=config.xlen

        self.en_i = Signal(bool(0)) # Fetch Data valid/ enable
        self.word_i = Signal(intbv(0)[xlen:]) # actual instruction to decode
        self.current_ip_i = Signal(modbv(0)[xlen:]) # ip (PC) of current instruction 
        self.next_ip_i = Signal(modbv(0)[xlen:]) # ip (PC) of next instruction 
        self.redirect_pending_i = Signal(bool(0))

class BackendOutputBundle:
    def __init__(self,config=def_config):
        self.config=config
        xlen=config.xlen

        self.jump_o =  Signal(bool(0))
        self.jump_dest_o =  Signal(intbv(0)[xlen:])
        self.busy_o = Signal(bool(0))

       

class SimpleBackend:
    def __init__(self,config=def_config):
        self.reg_portA = RFReadPort(xlen=config.xlen)
        self.reg_portB = RFReadPort(xlen=config.xlen)
        self.reg_writePort = RFWritePort(xlen=config.xlen)

        self.decode = DecodeBundle(config)
        self.execute =  ExecuteBundle(config)
        self.pipeline_events = PipelineBoundaryEventBundle(config)

        self.config=config 
        

    @block
    def backend(self,fetchBundle, frontEnd, databus, clock, reset, out, debugport, debugRegisterBundle=None):

        regfile_inst = RegisterFile(clock,self.reg_portA,self.reg_portB,self.reg_writePort,self.config.xlen)
        boundary_next_pc = Signal(modbv(self.config.reset_address)[self.config.xlen:])
        boundary_accepted = Signal(bool(0))
        boundary_accepted_source = Signal(modbv(PIPELINE_SOURCE_NORMAL)[2:])
        boundary_accepted_pc = Signal(modbv(0)[self.config.xlen:])
        trap_vector_pc = Signal(modbv(0)[self.config.xlen:])
        progbuf_active = Signal(bool(0))

        if self.config.enableDebugModule:
            register_transfer = AbstractRegisterTransferBundle(self.config)
            progbuf_issue = ProgbufIssueBundle(self.config)
            progbuf_completion = ProgbufCompletionBundle()
            pipeline_request = DebugPipelineRequestBundle(self.config)
            debug_pipeline_events = DebugPipelineEventBundle(self.config)

            decode_inst = self.decode.decoder(
                clock, reset, debugRegisterBundle=debugRegisterBundle,
                register_transfer=register_transfer)
            exec_inst = self.execute.SimpleExecute(
                self.decode, databus, debugport, clock, reset,
                debugRegisterBundle=debugRegisterBundle,
                debug_flush_i=pipeline_request.flush,
                debug_progbuf_active_i=progbuf_active)

            abstract_command_inst = AbstractCommandController(
                self.config, clock, debugRegisterBundle, register_transfer,
                progbuf_issue, progbuf_completion)
            hart_debug_inst = HartDebugController(
                self.config, clock, debugRegisterBundle,
                self.decode.debugCSRBundle, self.decode.debugCSRUpdateBundle,
                pipeline_request, debug_pipeline_events)
            pipeline_adapter_inst = DebugPipelineAdapter(
                self.config, clock, reset, fetchBundle, frontEnd, self.decode,
                pipeline_request, debug_pipeline_events, progbuf_issue,
                progbuf_completion, self.pipeline_events, trap_vector_pc,
                self.execute.debug_ebreak_o, self.execute.debug_ebreak_pc_o,
                self.execute.debug_progbuf_exception_o, progbuf_active)

            @always_comb
            def debug_boundary_issue():
                boundary_accepted.next = \
                    debug_pipeline_events.instruction_accepted or \
                    progbuf_completion.accepted
                boundary_accepted_pc.next = self.decode.current_ip_i
                if progbuf_completion.accepted:
                    boundary_accepted_source.next = \
                        PIPELINE_SOURCE_PROGRAM_BUFFER
                else:
                    boundary_accepted_source.next = PIPELINE_SOURCE_NORMAL
        else:
            decode_inst = self.decode.decoder(clock, reset)
            exec_inst = self.execute.SimpleExecute(
                self.decode, databus, debugport, clock, reset)

            @always_comb
            def normal_boundary_issue():
                boundary_accepted.next = self.decode.en_i and \
                    not self.decode.busy_o
                boundary_accepted_source.next = PIPELINE_SOURCE_NORMAL
                boundary_accepted_pc.next = self.decode.current_ip_i

        d_e_inst = self.execute.connect(clock,reset,previous=self.decode)

        if not self.config.enableDebugModule:
            f_d_inst = self.decode.connect(clock,reset,previous=frontEnd)

        @always_comb
        def comb():
            # Wire up register file

            self.reg_portA.ra.next = self.decode.rs1_adr_o
            self.reg_portB.ra.next = self.decode.rs2_adr_o

            self.decode.rs1_data_i.next = self.reg_portA.rd
            self.decode.rs2_data_i.next = self.reg_portB.rd 

            self.reg_writePort.wa.next = self.execute.rd_adr_o
            self.reg_writePort.we.next = self.execute.reg_we_o
            self.reg_writePort.wd.next = self.execute.result_o

            out.busy_o.next = self.decode.busy_o


        @always_comb
        def debugout():
            debugport.valid_o.next = self.execute.valid_o
            debugport.result_o.next = self.execute.result_o
            debugport.rd_adr_o.next = self.execute.rd_adr_o
            debugport.reg_we_o.next = self.execute.reg_we_o

        if not self.config.enableDebugModule:
            @always_comb
            def fetch_to_decode():
                self.decode.word_i.next = fetchBundle.word_i
                self.decode.current_ip_i.next = fetchBundle.current_ip_i
                self.decode.next_ip_i.next = fetchBundle.next_ip_i


        if self.config.enableDebugModule:
            @always_comb
            def proc_out():
                out.jump_o.next = self.execute.jump_o or pipeline_request.redirect_valid
                if pipeline_request.redirect_valid:
                    out.jump_dest_o.next = pipeline_request.redirect_pc
                else:
                    out.jump_dest_o.next = self.execute.jump_dest_o
        else:
            @always_comb
            def proc_out():
                out.jump_o.next = self.execute.jump_o
                out.jump_dest_o.next = self.execute.jump_dest_o

        @always_comb
        def trap_vector_comb():
            trap_vector_pc.next = \
                self.execute.trapCSR.mtvec << self.config.ip_low

        @always_comb
        def boundary_events_comb():
            pipeline_empty = not self.decode.valid_o and \
                not self.execute.busy_o and not self.execute.valid_o
            exception = self.execute.trap_request.valid
            completed = self.execute.retire_o and not exception
            terminal = completed or exception

            self.pipeline_events.accepted.next = boundary_accepted
            self.pipeline_events.accepted_source.next = \
                boundary_accepted_source
            self.pipeline_events.accepted_pc.next = boundary_accepted_pc
            self.pipeline_events.valid.next = terminal
            if progbuf_active:
                self.pipeline_events.source.next = \
                    PIPELINE_SOURCE_PROGRAM_BUFFER
            else:
                self.pipeline_events.source.next = PIPELINE_SOURCE_NORMAL

            self.pipeline_events.terminal.next = terminal
            self.pipeline_events.completed.next = completed
            self.pipeline_events.retired.next = completed
            self.pipeline_events.exception.next = exception
            self.pipeline_events.trap.next = exception
            self.pipeline_events.cancelled.next = False
            self.pipeline_events.killed.next = False
            self.pipeline_events.instruction_pc.next = \
                self.decode.debug_current_ip_o

            next_pc = boundary_next_pc
            if terminal and not progbuf_active:
                next_pc = self.execute.next_pc_o
            self.pipeline_events.next_pc.next = next_pc
            self.pipeline_events.redirect.next = self.execute.jump_o
            self.pipeline_events.redirect_pc.next = self.execute.jump_dest_o
            self.pipeline_events.register_write.next = \
                completed and self.execute.reg_we_o
            self.pipeline_events.register_address.next = \
                self.execute.rd_adr_o
            self.pipeline_events.register_data.next = self.execute.result_o
            self.pipeline_events.store_commit.next = \
                completed and self.decode.store_cmd
            self.pipeline_events.pipeline_empty.next = pipeline_empty
            self.pipeline_events.drained.next = pipeline_empty

        if self.config.enableDebugModule:
            @always_seq(clock.posedge, reset=reset)
            def boundary_next_pc_seq():
                if self.pipeline_events.terminal and not progbuf_active:
                    boundary_next_pc.next = self.execute.next_pc_o
                if pipeline_request.redirect_valid:
                    boundary_next_pc.next = pipeline_request.redirect_pc
        else:
            @always_seq(clock.posedge, reset=reset)
            def boundary_next_pc_seq():
                if self.pipeline_events.terminal:
                    boundary_next_pc.next = self.execute.next_pc_o


        return instances()

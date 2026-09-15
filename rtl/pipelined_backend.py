"""Four-stage Bonfire backend with functional-unit result registers.

ALU, load/store, CSR and jump-link values are registered independently. The
writeback result mux therefore sits after those registers while preserving
the architectural four-stage timing.
"""

from myhdl import *

from rtl.decode import DecodeBundle
from rtl.execute import ExecuteBundle
from rtl.regfile import RFReadPort, RFWritePort, RegisterFile
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
from rtl.bonfire_interfaces import (
    PIPELINE_SOURCE_NORMAL,
    PIPELINE_SOURCE_PROGRAM_BUFFER,
    PipelineBoundaryEventBundle,
)


class PipelinedBackend:
    def __init__(self, config):
        assert config.pipeline_length == 4

        self.config = config
        self.reg_portA = RFReadPort(xlen=config.xlen)
        self.reg_portB = RFReadPort(xlen=config.xlen)
        self.reg_writePort = RFWritePort(xlen=config.xlen)

        self.decode = DecodeBundle(config)
        self.execute = ExecuteBundle(config)
        self.pipeline_events = PipelineBoundaryEventBundle(config)

    @block
    def backend(self, fetchBundle, frontEnd, databus, clock, reset, out,
                debugport, debugRegisterBundle=None):
        conf = self.config
        bypass = conf.writeback_bypass
        boundary_next_pc = Signal(modbv(conf.reset_address)[conf.xlen:])
        boundary_accepted = Signal(bool(0))
        boundary_accepted_source = Signal(modbv(PIPELINE_SOURCE_NORMAL)[2:])
        boundary_accepted_pc = Signal(modbv(0)[conf.xlen:])
        progbuf_active = Signal(bool(0))

        regfile_inst = RegisterFile(
            clock, self.reg_portA, self.reg_portB,
            self.reg_writePort, conf.xlen)
        if conf.enableDebugModule:
            register_transfer = AbstractRegisterTransferBundle(conf)
            progbuf_issue = ProgbufIssueBundle(conf)
            progbuf_completion = ProgbufCompletionBundle()
            pipeline_request = DebugPipelineRequestBundle(conf)
            debug_pipeline_events = DebugPipelineEventBundle(conf)

            decode_inst = self.decode.decoder(
                clock, reset, debugRegisterBundle=debugRegisterBundle,
                register_transfer=register_transfer)
            exec_inst = self.execute.SimpleExecute(
                self.decode, databus, debugport, clock, reset,
                debugRegisterBundle=debugRegisterBundle,
                debug_flush_i=pipeline_request.flush,
                debug_progbuf_active_i=progbuf_active)
        else:
            decode_inst = self.decode.decoder(clock, reset)
            exec_inst = self.execute.SimpleExecute(
                self.decode, databus, debugport, clock, reset)
        d_e_inst = self.execute.connect(clock, reset, previous=self.decode)
        if not conf.enableDebugModule:
            f_d_inst = self.decode.connect(clock, reset, previous=frontEnd)

        wb_valid = Signal(bool(0))
        wb_we = Signal(bool(0))
        wb_rd = Signal(modbv(0)[5:])
        wb_alu_valid = Signal(bool(0))
        wb_load_valid = Signal(bool(0))
        wb_csr_valid = Signal(bool(0))
        wb_jump_valid = Signal(bool(0))
        wb_alu_data = Signal(modbv(0)[conf.xlen:])
        wb_load_data = Signal(modbv(0)[conf.xlen:])
        wb_csr_data = Signal(modbv(0)[conf.xlen:])
        wb_jump_data = Signal(modbv(0)[conf.xlen:])
        wb_data = Signal(modbv(0)[conf.xlen:])
        wb_control_retire = Signal(bool(0))
        wb_pc = Signal(modbv(0)[conf.xlen:])
        wb_next_pc = Signal(modbv(conf.reset_address)[conf.xlen:])
        wb_store = Signal(bool(0))
        wb_progbuf = Signal(bool(0))
        wb_redirect = Signal(bool(0))
        wb_redirect_pc = Signal(modbv(0)[conf.xlen:])

        @always_seq(clock.posedge, reset=reset)
        def writeback_seq():
            wb_valid.next = self.execute.valid_o
            wb_we.next = self.execute.reg_we_o
            wb_rd.next = self.execute.rd_adr_o
            wb_alu_valid.next = self.execute.alu_valid_o
            wb_load_valid.next = self.execute.load_valid_o
            wb_csr_valid.next = self.execute.csr_valid_o
            wb_jump_valid.next = self.execute.jump_valid_o

            wb_alu_data.next = self.execute.alu.res_o
            wb_load_data.next = self.execute.ls.result_o
            wb_csr_data.next = self.execute.csr.result_o
            wb_jump_data.next = self.decode.next_ip_o
            wb_control_retire.next = self.execute.retire_o and \
                not self.execute.valid_o

            if self.execute.retire_o:
                wb_pc.next = self.decode.debug_current_ip_o
                wb_next_pc.next = self.execute.next_pc_o
                wb_store.next = self.decode.store_cmd
                wb_progbuf.next = progbuf_active
                wb_redirect.next = self.execute.redirect_o
                wb_redirect_pc.next = self.execute.next_pc_o

        @always_comb
        def writeback_result_mux():
            if wb_alu_valid:
                wb_data.next = wb_alu_data
            elif wb_load_valid:
                wb_data.next = wb_load_data
            elif wb_jump_valid:
                wb_data.next = wb_jump_data
            elif wb_csr_valid:
                wb_data.next = wb_csr_data
            else:
                wb_data.next = 0

        if bypass:
            @always_comb
            def forward_comb():
                self.execute.forward_we_i.next = wb_valid and wb_we
                self.execute.forward_rd_i.next = wb_rd
                self.execute.forward_data_i.next = wb_data
                self.execute.hazard_i.next = False
        else:
            @always_comb
            def four_stage_hazard():
                hazard_rs1 = wb_valid and wb_we and wb_rd != 0 and \
                    self.decode.valid_o and self.decode.uses_rs1_o and \
                    self.decode.source_rs1_o == wb_rd

                hazard_rs2 = wb_valid and wb_we and wb_rd != 0 and \
                    self.decode.valid_o and self.decode.uses_rs2_o and \
                    self.decode.source_rs2_o == wb_rd
                self.execute.hazard_i.next = hazard_rs1 or hazard_rs2

        @always_comb
        def common_comb():
            self.reg_portA.ra.next = self.decode.rs1_adr_o
            self.reg_portB.ra.next = self.decode.rs2_adr_o

            self.decode.rs1_data_i.next = self.reg_portA.rd
            self.decode.rs2_data_i.next = self.reg_portB.rd

            self.reg_writePort.wa.next = wb_rd
            self.reg_writePort.we.next = wb_valid and wb_we
            self.reg_writePort.wd.next = wb_data

            out.busy_o.next = self.decode.busy_o

        @always_comb
        def debugout():
            debugport.valid_o.next = wb_valid
            debugport.result_o.next = wb_data
            debugport.rd_adr_o.next = wb_rd
            debugport.reg_we_o.next = wb_valid and wb_we

        if conf.enableDebugModule:
            abstract_command_inst = AbstractCommandController(
                conf, clock, debugRegisterBundle, register_transfer,
                progbuf_issue, progbuf_completion)
            hart_debug_inst = HartDebugController(
                conf, clock, debugRegisterBundle,
                self.decode.debugCSRBundle, self.decode.debugCSRUpdateBundle,
                pipeline_request, debug_pipeline_events)
            pipeline_adapter_inst = DebugPipelineAdapter(
                conf, clock, fetchBundle, frontEnd, self.decode,
                pipeline_request, debug_pipeline_events, progbuf_issue,
                progbuf_completion, self.pipeline_events,
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

            @always_comb
            def proc_out():
                out.jump_o.next = self.execute.jump_o or pipeline_request.redirect_valid
                if pipeline_request.redirect_valid:
                    out.jump_dest_o.next = pipeline_request.redirect_pc
                else:
                    out.jump_dest_o.next = self.execute.jump_dest_o
        else:
            @always_comb
            def fetch_to_decode():
                self.decode.word_i.next = fetchBundle.word_i
                self.decode.current_ip_i.next = fetchBundle.current_ip_i
                self.decode.next_ip_i.next = fetchBundle.next_ip_i

            @always_comb
            def normal_boundary_issue():
                boundary_accepted.next = self.decode.en_i and \
                    not self.decode.busy_o
                boundary_accepted_source.next = PIPELINE_SOURCE_NORMAL
                boundary_accepted_pc.next = self.decode.current_ip_i

            @always_comb
            def proc_out():
                out.jump_o.next = self.execute.jump_o
                out.jump_dest_o.next = self.execute.jump_dest_o

        @always_comb
        def boundary_events_comb():
            pipeline_empty = not self.decode.valid_o and \
                not self.execute.busy_o and not self.execute.valid_o and \
                not wb_valid and not wb_control_retire
            exception = self.execute.trap_request.valid
            completed = (wb_valid or wb_control_retire) and not exception
            terminal = completed or exception

            self.pipeline_events.accepted.next = boundary_accepted
            self.pipeline_events.accepted_source.next = \
                boundary_accepted_source
            self.pipeline_events.accepted_pc.next = boundary_accepted_pc
            self.pipeline_events.valid.next = terminal
            if exception:
                self.pipeline_events.source.next = \
                    self.execute.trap_request.source
            elif wb_progbuf:
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
            if exception:
                self.pipeline_events.instruction_pc.next = \
                    self.decode.debug_current_ip_o
            else:
                self.pipeline_events.instruction_pc.next = wb_pc

            next_pc = boundary_next_pc
            if exception and not progbuf_active:
                next_pc = self.execute.next_pc_o
            elif completed and not wb_progbuf:
                next_pc = wb_next_pc
            self.pipeline_events.next_pc.next = next_pc

            if exception:
                self.pipeline_events.redirect.next = \
                    self.execute.redirect_o and not progbuf_active
                self.pipeline_events.redirect_pc.next = self.execute.next_pc_o
            else:
                self.pipeline_events.redirect.next = wb_redirect
                self.pipeline_events.redirect_pc.next = wb_redirect_pc
            self.pipeline_events.register_write.next = completed and wb_valid and wb_we
            self.pipeline_events.register_address.next = wb_rd
            self.pipeline_events.register_data.next = wb_data
            self.pipeline_events.store_commit.next = completed and wb_valid and wb_store
            self.pipeline_events.pipeline_empty.next = pipeline_empty
            self.pipeline_events.drained.next = pipeline_empty

        if conf.enableDebugModule:
            @always_seq(clock.posedge, reset=reset)
            def boundary_next_pc_seq():
                if self.pipeline_events.terminal:
                    if self.execute.trap_request.valid and not progbuf_active:
                        boundary_next_pc.next = self.execute.next_pc_o
                    elif not self.execute.trap_request.valid and not wb_progbuf:
                        boundary_next_pc.next = wb_next_pc
                if pipeline_request.redirect_valid:
                    boundary_next_pc.next = pipeline_request.redirect_pc
        else:
            @always_seq(clock.posedge, reset=reset)
            def boundary_next_pc_seq():
                if self.pipeline_events.terminal:
                    if self.execute.trap_request.valid:
                        boundary_next_pc.next = self.execute.next_pc_o
                    else:
                        boundary_next_pc.next = wb_next_pc

        return instances()

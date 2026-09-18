"""
RISC-V execution stage
(c) 2019 The Bonfire Project
License: See LICENSE
"""
from __future__ import print_function

from myhdl import *

from rtl import alu, loadstore, csr, trap
from rtl.execute_control import ExecuteControlBundle
from rtl.machine_extension import MachineExtensionControllerBundle

from rtl.instructions import ArithmeticFunct3 as a3

from rtl.pipeline_control import *
from rtl.bonfire_interfaces import TrapRequestBundle


class ExecuteBundle(PipelineControl):
    def __init__(self,config):
        #config
        self.config = config

        xlen = config.xlen

        self.wb_stage = config.pipeline_length==4

        #functional units
        self.alu=alu.AluBundle(xlen)
        self.ls = loadstore.LoadStoreBundle(config)
        self.csr =csr.CSRUnitBundle(config)
        self.trapCSR = trap.TrapCSRBundle(config)
        self.csrUpdate = trap.TrapCSRUpdateBundle(config)

        # output
        self.result_o = Signal(intbv(0)[xlen:])

        if self.wb_stage:
            # Mutually exclusive result selectors. The source-registered
            # four-stage backend registers these one-hot signals with their
            # respective functional-unit values and performs its mux afterwards.
            self.alu_valid_o = Signal(bool(0))
            self.load_valid_o = Signal(bool(0))
            self.csr_valid_o = Signal(bool(0))
            self.jump_valid_o = Signal(bool(0))
            self.m_valid_o = Signal(bool(0))

        self.reg_we_o = Signal(bool(0)) # Register File Write Enable
        self.rd_adr_o =  Signal(modbv(0)[5:]) # Target register

        self.jump_o = Signal(bool(0)) # Branch/jump
        self.jump_dest_o = Signal(intbv(0)[xlen:])

        self.invalid_opcode_fault = Signal(bool(0))
        self.trap_request = TrapRequestBundle(config)
        self.retire_o = Signal(bool(0))
        self.control_retire_o = Signal(bool(0))
        self.next_pc_o = Signal(modbv(0)[xlen:])
        self.redirect_o = Signal(bool(0))

        if config.enableDebugModule:
            self.debug_ebreak_o = Signal(bool(0))
            self.debug_ebreak_pc_o = Signal(modbv(0)[xlen:])
            self.debug_progbuf_exception_o = Signal(bool(0))

        # Optional downstream interlock and writeback forwarding.

        if config.writeback_bypass:
            self.forward_we_i = Signal(bool(0))
            self.forward_rd_i = Signal(modbv(0)[5:])
            self.forward_data_i = Signal(modbv(0)[xlen:])

        self.hazard_i = Signal(bool(0)) # Always instanziated but only used with 4 Stage Pipeline without Bypass

        PipelineControl.__init__(self)



    @block
    def SimpleExecute(
        self, decode, databus, debugport, clock, reset,
        debugRegisterBundle=None, debug_flush_i=None,
        debug_progbuf_active_i=None,
    ):
        """
        Simple execution Unit designed for single stage in-order execution
        decode : DecodeBundle class instance
        databus : DBusBundle instance
        debugport : DebugOutputBundle instance
        clock : clock
        reset : reset
        """

        assert self.config.loadstore_outstanding==1, "SimpleExecute requires config.loadstore_outstanding==1"
        assert not self.config.RVC, "Compressed ISA not implemented yet"

        busy = Signal(bool(0))
        valid = Signal(bool(0))
        rd_adr_reg = Signal(modbv(0)[5:])

        if not self.wb_stage:
            # Decode may already hold the following instruction when a
            # multi-cycle unit retires. Therefore loads and pipelined shifts
            # use the instruction class captured at issue, while single-cycle
            # ALU and CSR operations use the current registered decode class.
            load_pending = Signal(bool(0))
            shift_pending = Signal(bool(0))
            pipelined_shifter = self.config.shifter_mode == "pipelined"

        debug_ebreak_enable = Signal(bool(0))
        retire = Signal(bool(0))
        counter_retire = Signal(bool(0))
        alu_success = Signal(bool(0))
        ls_success = Signal(bool(0))

        op1 = Signal(modbv(0)[self.config.xlen:])
        op2 = Signal(modbv(0)[self.config.xlen:])
        branch_equal = Signal(bool(0))
        branch_ge = Signal(bool(0))
        branch_uge = Signal(bool(0))

        alu_inst = self.alu.alu(clock,reset,self.config.shifter_mode )
        ls_inst = self.ls.LoadStoreUnit(databus,clock,reset)

        machine_extension = MachineExtensionControllerBundle(self.config)
        machine_extension_inst = machine_extension.controller(clock, reset)
        m_complete = machine_extension.port.valid_o
        m_wait = machine_extension.port.busy_o
        m_result = machine_extension.port.result_o
        m_rd = machine_extension.rd_o

        @always_comb
        def machine_extension_connect():
            machine_extension.port.op1_i.next = op1
            machine_extension.port.op2_i.next = op2
            machine_extension.port.operation_i.next = decode.funct3_o
            machine_extension.port.request_i.next = decode.m_cmd
            machine_extension.port.cancel_i.next = debug_flush
            machine_extension.rd_i.next = decode.rd_adr_o
            machine_extension.hazard_i.next = self.hazard_i
            machine_extension.consume_i.next = self.taken

        if self.config.enableDebugModule:
            csr_inst = self.csr.CSRUnit(
                self.trapCSR,self.csrUpdate,clock,reset,
                debugCSRBundle=decode.debugCSRBundle,
                debugCSRUpdateBundle=decode.debugCSRUpdateBundle,
                debugRegisterBundle=debugRegisterBundle,
                retire_i=counter_retire
                if self.wb_stage and self.config.writeback_bypass else retire)
        else:
            csr_inst = self.csr.CSRUnit(
                self.trapCSR, self.csrUpdate, clock, reset,
                retire_i=counter_retire
                if self.wb_stage and self.config.writeback_bypass else retire)

        p_inst = self.pipeline_instance(busy,valid)

        if self.config.enableDebugModule:
            debug_ebreak_enable = decode.debugCSRBundle.ebreakm
            assert debug_flush_i is not None, "debug execute requires debug_flush_i"
            assert debug_progbuf_active_i is not None, "debug execute requires progbuf activity"
            debug_flush = debug_flush_i
            debug_progbuf_active = debug_progbuf_active_i
        else:
            debug_flush = False
            debug_progbuf_active = False

        execute_control = ExecuteControlBundle(self.config)
        execute_control_inst = execute_control.controller(
            decode, self.alu.res_o, branch_equal, branch_ge, branch_uge,
            self.ls, self.csr, self.trapCSR,
            self.csrUpdate, self.trap_request, op1, op2, self.taken,
            clock, reset, debug_ebreak_enable, debug_progbuf_active)
        jump = execute_control.jump_decision_o
        jump_we = execute_control.jump_write_o
        jump_busy = execute_control.jump_busy_o
        trap_valid = execute_control.trap_valid_o
        trap_pending = execute_control.trap_pending_o
        ls_issue_invalid = execute_control.ls_issue_invalid_o
        ls_issue_misaligned = execute_control.ls_issue_misaligned_o
        jalr_misaligned = execute_control.jalr_misaligned_o
        control_retire = execute_control.control_retire_o

        if self.config.enableDebugModule:
            @always_comb
            def debug_events():
                self.debug_ebreak_o.next = execute_control.debug_ebreak_o
                self.debug_ebreak_pc_o.next = \
                    execute_control.debug_ebreak_pc_o
                if self.config.jump_bypass:
                    self.debug_progbuf_exception_o.next = \
                        debug_progbuf_active and trap_valid
                else:
                    self.debug_progbuf_exception_o.next = trap_pending and \
                        execute_control.trap_pending_progbuf_o

        @always_seq(clock.posedge,reset=reset)
        def seq():
            counter_retire.next = retire

            if self.taken:
                rd_adr_reg.next = decode.rd_adr_o

        if not self.wb_stage:
            @always_seq(clock.posedge, reset=reset)
            def pending_seq():
                if self.taken:
                    load_pending.next = decode.load_cmd and \
                        not ls_issue_invalid and not ls_issue_misaligned
                    shift_pending.next = pipelined_shifter and decode.alu_cmd and \
                        not decode.m_cmd and \
                        (decode.funct3_o == a3.RV32_F3_SLL or \
                         decode.funct3_o == a3.RV32_F3_SRL_SRA)
                else:
                    if self.ls.valid_o:
                        load_pending.next = False
                    if self.alu.valid_o:
                        shift_pending.next = False

        if self.config.writeback_bypass:
            @always_comb
            def frwd_comb():
                op1.next = decode.op1_o
                op2.next = decode.op2_o
                if self.forward_we_i and self.forward_rd_i != 0:
                    if decode.uses_rs1_o and decode.source_rs1_o == self.forward_rd_i:
                        op1 .next= self.forward_data_i
                    if decode.uses_rs2_o and decode.source_rs2_o == self.forward_rd_i:
                        op2.next  = self.forward_data_i
        else:
            @always_comb
            def op_comb():
                op1.next = decode.op1_o
                op2.next = decode.op2_o


        @always_comb
        def comb():

            # ALU Input wirings
            self.alu.funct3_i.next = decode.funct3_o
            self.alu.funct7_6_i.next = decode.funct7_o[5]
            self.alu.op1_i.next = op1
            self.alu.op2_i.next = op2
            branch_equal.next = self.alu.flag_equal
            branch_ge.next = self.alu.flag_ge
            branch_uge.next = self.alu.flag_uge

            # LS Unit Input wirings
            self.ls.funct3_i.next = decode.funct3_o
            self.ls.op1_i.next = op1
            self.ls.op2_i.next = op2
            self.ls.displacement_i.next = decode.displacement_o
            self.ls.store_i.next = decode.store_cmd

            #csr Unit Input Wirings
            self.csr.csr_adr.next = decode.priv_funct_12
            self.csr.op1_i.next = op1
            self.csr.funct3_i.next = decode.funct3_o
            self.csr.source_i.next = decode.source_rs1_o

            # Pipeline
            busy.next = self.alu.busy_o or self.ls.busy_o or \
                self.csr.busy_o or jump_busy or self.hazard_i or m_wait
            valid.next = alu_success or ls_success or \
                self.csr.valid_o or jump_we or m_complete

            if self.config.jump_bypass:
                if self.config.enableDebugModule:
                    decode.kill_i.next = (self.taken and jump) or \
                        trap_valid or debug_flush
                else:
                    decode.kill_i.next = self.taken and jump
            else:
                if self.config.enableDebugModule:
                    decode.kill_i.next = jump_busy or trap_valid or \
                        trap_pending or debug_flush
                else:
                    decode.kill_i.next = jump_busy or trap_valid or \
                        trap_pending


            # Functional Unit selection

            self.alu.en_i.next = decode.alu_cmd and not decode.m_cmd and \
                self.taken
            self.ls.en_i.next = (decode.store_cmd or decode.load_cmd) and \
                self.taken and not ls_issue_invalid and \
                not ls_issue_misaligned
            self.csr.en_i.next = decode.csr_cmd and self.taken

            # Simulation Debug Signals
            debugport.jump_exec.next = self.taken and ( decode.branch_cmd or decode.jump_cmd or decode.jumpr_cmd)
            debugport.jump.next = jump



        if self.wb_stage:
            @always_comb
            def wb_prepare():
                # The ordinary sources are captured from their dedicated
                # functional-unit buses.  result_o carries the registered
                # RV32M completion value for the additional writeback source.
                self.result_o.next = m_result
                self.alu_valid_o.next = False
                self.load_valid_o.next = False
                self.csr_valid_o.next = False
                self.jump_valid_o.next = False
                self.m_valid_o.next = False

                # The source selector is registered together with the functional
                # unit results. Completion signals can therefore identify the
                # retiring source directly; JALR needs jump-link priority over
                # the simultaneously valid ALU result used as its target.
                if jump_we:
                    self.jump_valid_o.next = True
                elif m_complete:
                    self.m_valid_o.next = True
                elif self.ls.we_o and ls_success:
                    self.load_valid_o.next = True
                elif alu_success:
                    self.alu_valid_o.next = True
                elif self.csr.valid_o:
                    self.csr_valid_o.next = True

        else:
            @always_comb
            def result_mux():
                # result_o is an unqualified data bus. The selected source may
                # drive it while a multi-cycle operation is still pending; its
                # value is only valid in the retire cycle, when execute.valid_o
                # (and reg_we_o for a register write) qualifies it.

                if jump_we:
                    self.result_o.next = decode.next_ip_o
                elif m_complete:
                    self.result_o.next = m_result
                elif load_pending:
                    self.result_o.next = self.ls.result_o
                elif shift_pending or (decode.alu_cmd and not decode.m_cmd):
                    self.result_o.next = self.alu.res_o
                elif decode.csr_cmd:
                    self.result_o.next = self.csr.result_o
                else:
                    self.result_o.next = 0


        @always_comb
        def comb_misc():

            # Each functional unit qualifies its own successful completion.
            # A global ``not trap_valid`` term made the complete exception
            # classifier part of the primary Execute-to-Writeback valid path.
            alu_success.next = self.alu.valid_o and \
                not decode.invalid_opcode and \
                not (decode.jumpr_cmd and jalr_misaligned)
            ls_success.next = self.ls.valid_o and not self.ls.bus_error_o
            self.reg_we_o.next = alu_success or m_complete or \
                (self.ls.we_o and ls_success) or self.csr.valid_o or jump_we
            self.retire_o.next = retire

            if m_complete:
                self.rd_adr_o.next = m_rd
            elif self.taken:
                self.rd_adr_o.next = decode.rd_adr_o
            else:
                self.rd_adr_o.next = rd_adr_reg

            self.jump_o.next = execute_control.jump_o
            self.jump_dest_o.next = execute_control.jump_dest_o
            self.redirect_o.next = execute_control.redirect_o
            self.next_pc_o.next = execute_control.next_pc_o
            self.invalid_opcode_fault.next = \
                execute_control.invalid_opcode_fault_o


        @always_comb
        def retirement_event():
            retire.next = valid or control_retire
            self.control_retire_o.next = control_retire

            #TODO: Implement other functional units


        return instances()

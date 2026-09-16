"""
RISC-V execution stage
(c) 2019 The Bonfire Project
License: See LICENSE
"""
from __future__ import print_function

from myhdl import *

from rtl import alu, loadstore, csr, trap
from rtl.divider import DividerBundle
from rtl.multiplier import MultiplierBundle

from rtl.instructions import ArithmeticFunct3 as a3
from rtl.instructions import BranchFunct3  as b3
from rtl.instructions import Opcodes

from rtl.pipeline_control import *
from rtl.bonfire_interfaces import (
    PIPELINE_SOURCE_NORMAL,
    PIPELINE_SOURCE_PROGRAM_BUFFER,
    TrapRequestBundle,
)


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

        jump = Signal(bool(0))
        jump_r =  Signal(bool(0))
        jump_dest =  Signal(intbv(0)[self.config.xlen:])
        jump_dest_r = Signal(intbv(0)[self.config.xlen:])
        normal_jump = Signal(bool(0))
        normal_jump_dest = Signal(intbv(0)[self.config.xlen:])
        jump_busy = Signal(bool(0)) # Only used when not config.jump_bypass

        if not self.wb_stage:
            # Decode may already hold the following instruction when a
            # multi-cycle unit retires. Therefore loads and pipelined shifts
            # use the instruction class captured at issue, while single-cycle
            # ALU and CSR operations use the current registered decode class.
            load_pending = Signal(bool(0))
            shift_pending = Signal(bool(0))
            pipelined_shifter = self.config.shifter_mode == "pipelined"

        jump_we = Signal(bool(0)) # rd write enable on jal/jalr
        debug_ebreak_enable = Signal(bool(0))
        debug_ebreak = Signal(bool(0))
        debug_ebreak_pc = Signal(modbv(0)[self.config.xlen:])

        ls_effective_address = Signal(modbv(0)[self.config.xlen:])
        ls_issue_invalid = Signal(bool(0))
        ls_issue_misaligned = Signal(bool(0))
        jalr_misaligned = Signal(bool(0))
        ls_fault_address = Signal(modbv(0)[self.config.xlen:])
        ls_fault_pc = Signal(modbv(0)[self.config.xlen:])
        ls_fault_store = Signal(bool(0))
        trap_valid = Signal(bool(0))
        trap_cause = Signal(modbv(0)[6:])
        trap_epc = Signal(modbv(0)[self.config.xlen:])
        trap_tval = Signal(modbv(0)[self.config.xlen:])
        trap_pending = Signal(bool(0))
        trap_pending_cause = Signal(modbv(0)[6:])
        trap_pending_epc = Signal(modbv(0)[self.config.xlen:])
        trap_pending_jalr = Signal(bool(0))
        trap_pending_alu_tval = Signal(modbv(0)[self.config.xlen:])
        trap_pending_jump_tval = Signal(modbv(0)[self.config.xlen:])
        trap_pending_instruction = Signal(modbv(0)[self.config.xlen:])
        registered_trap_tval = Signal(modbv(0)[self.config.xlen:])
        trap_pending_progbuf = Signal(bool(0))
        retire = Signal(bool(0))
        control_retire = Signal(bool(0))
        counter_retire = Signal(bool(0))
        alu_success = Signal(bool(0))
        ls_success = Signal(bool(0))

        # RV32M issue is single-shot: Decode remains stalled while the
        # selected unit is active and is released in the registered completion
        # cycle.  The result itself never feeds the busy/control path.
        m_pending = Signal(bool(0))
        m_start = Signal(bool(0))
        m_complete = Signal(bool(0))
        m_wait = Signal(bool(0))
        m_result = Signal(modbv(0)[self.config.xlen:])
        m_cancel = Signal(bool(0))
        m_rd = Signal(modbv(0)[5:])
        m_release = Signal(bool(0))

        op1 = Signal(modbv(0)[self.config.xlen:])
        op2 = Signal(modbv(0)[self.config.xlen:])

        alu_inst = self.alu.alu(clock,reset,self.config.shifter_mode )
        ls_inst = self.ls.LoadStoreUnit(databus,clock,reset)

        if self.config.enable_m_extension:
            multiplier = MultiplierBundle(self.config.xlen)
            divider = DividerBundle(self.config.xlen)
            multiplier_inst = multiplier.multiplier(clock, reset)
            divider_inst = divider.divider(clock, reset)

            @always_comb
            def m_unit_connect():
                funct3 = decode.funct3_o
                is_division = bool(funct3[2])

                # m_cmd is a registered, valid-qualified command.  Depending
                # on it directly avoids the combinational
                # decode.valid -> Execute busy -> Decode stall loop.
                m_start.next = decode.m_cmd and \
                    not m_pending and not m_release and \
                    not self.hazard_i
                m_cancel.next = debug_flush
                m_complete.next = multiplier.ce_o or divider.ce_o
                # Keep Decode stalled throughout the completion cycle.  A
                # following release cycle consumes the held instruction but
                # suppresses a second request.
                m_wait.next = m_pending or \
                    (decode.m_cmd and not m_release)

                if divider.ce_o:
                    m_result.next = divider.result_o
                else:
                    m_result.next = multiplier.result_o

                multiplier.op1_i.next = op1
                multiplier.op2_i.next = op2
                multiplier.ce_i.next = m_start and not is_division
                multiplier.cancel_i.next = m_cancel
                multiplier.high_i.next = funct3 != 0
                multiplier.signed_a_i.next = \
                    funct3 == 1 or funct3 == 2
                multiplier.signed_b_i.next = funct3 == 1

                divider.op1_i.next = op1
                divider.op2_i.next = op2
                divider.ce_i.next = m_start and is_division
                divider.cancel_i.next = m_cancel
                divider.signed_i.next = funct3 == 4 or funct3 == 6
                divider.rem_i.next = funct3 == 6 or funct3 == 7

            @always_seq(clock.posedge, reset=reset)
            def m_pending_seq():
                if m_cancel:
                    m_pending.next = False
                    m_release.next = False
                elif m_start:
                    m_pending.next = True
                    m_release.next = False
                    m_rd.next = decode.rd_adr_o
                elif m_complete:
                    m_pending.next = False
                    m_release.next = True
                elif m_release and self.taken:
                    m_release.next = False
        else:
            @always_comb
            def m_disabled():
                # Keep a real sensitivity input for MyHDL while producing
                # constants after elaboration (m_cmd is never asserted when
                # the extension is disabled).
                m_start.next = decode.m_cmd and False
                m_complete.next = decode.m_cmd and False
                m_wait.next = decode.m_cmd and False
                if decode.m_cmd:
                    m_result.next = op1
                else:
                    m_result.next = 0
                m_cancel.next = decode.m_cmd and debug_flush

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

            @always_comb
            def debug_events():
                self.debug_ebreak_o.next = debug_ebreak
                self.debug_ebreak_pc_o.next = debug_ebreak_pc
                if self.config.jump_bypass:
                    self.debug_progbuf_exception_o.next = \
                        debug_progbuf_active and trap_valid
                else:
                    self.debug_progbuf_exception_o.next = \
                        trap_pending and trap_pending_progbuf
        else:
            debug_flush = False
            debug_progbuf_active = False


        @always_seq(clock.posedge,reset=reset)
        def seq():

            jump_busy.next = False
            counter_retire.next = retire
            trap_pending.next = False
            trap_pending_cause.next = trap_cause
            trap_pending_epc.next = trap_epc
            trap_pending_jalr.next = decode.jumpr_cmd
            trap_pending_alu_tval.next = self.alu.res_o & ~1
            trap_pending_jump_tval.next = decode.jump_dest_o
            trap_pending_instruction.next = decode.debug_word_o
            trap_pending_progbuf.next = debug_progbuf_active

            if trap_valid:
                trap_pending.next = True

            if self.taken:
                rd_adr_reg.next = decode.rd_adr_o

            if self.config.jump_bypass:
                if trap_valid:
                    jump_dest_r.next = jump_dest
                    jump_r.next = jump
                elif self.taken:
                    jump_dest_r.next = jump_dest
                    jump_r.next = jump
            elif self.taken:
                # Machine traps use the separately registered trap event below.
                # Keep the normal redirect register independent from the
                # exception classifier and its metadata muxes.
                jump_dest_r.next = normal_jump_dest
                jump_r.next = normal_jump
                jump_busy.next = normal_jump
                # # Debug code
                # if self.debug_exec_jump.next:
                #     print(now(), "jump or branch")

            if self.taken and (decode.load_cmd or decode.store_cmd):
                ls_fault_address.next = ls_effective_address

            if self.ls.taken:
                ls_fault_pc.next = decode.mepc_o
                ls_fault_store.next = decode.store_cmd

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
                    decode.kill_i.next = jump_busy or trap_pending or \
                        debug_flush
                else:
                    decode.kill_i.next = jump_busy


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

            if trap_valid and self.config.jump_bypass:
                self.jump_o.next = jump
                self.jump_dest_o.next = jump_dest
            elif self.taken and self.config.jump_bypass:
                self.jump_o.next = jump
                self.jump_dest_o.next = jump_dest
            elif trap_pending and not self.config.jump_bypass:
                self.jump_o.next = not trap_pending_progbuf
                self.jump_dest_o.next = \
                    self.trapCSR.mtvec << self.config.ip_low
            else:
                self.jump_o.next = jump_r and not self.taken # supress jump_o when next instruction after jump is taken
                self.jump_dest_o.next = jump_dest_r


        @always_comb
        def mcause_update():
            # mcause comb logic. Aware that actual update of the mcause csr is enabled
            # by  elf.csrUpdate.we_mcause.next

            self.csrUpdate.mcause_irq.next = 0

            if self.config.jump_bypass:
                self.csrUpdate.mcause.next = trap_cause
            else:
                self.csrUpdate.mcause.next = trap_pending_cause

        @always_comb
        def loadstore_address_comb():
            ls_effective_address.next = \
                op1 + decode.displacement_o.signed()

        @always_comb
        def loadstore_issue_check():
            funct = decode.funct3_o
            byte_mode = funct[2:0] == 0
            half_mode = funct[2:0] == 1
            word_mode = funct[2:0] == 2
            address_bit0 = bool(op1[0]) != bool(decode.displacement_o[0])
            address_bit1 = \
                (bool(op1[1]) != bool(decode.displacement_o[1])) != \
                (bool(op1[0]) and bool(decode.displacement_o[0]))

            ls_issue_invalid.next = funct[2] and decode.store_cmd or not (
                byte_mode or half_mode or word_mode)
            ls_issue_misaligned.next = \
                (half_mode and address_bit0) or \
                (word_mode and (address_bit0 or address_bit1))

            # RVC is not supported, so JALR is aligned when bit one of the
            # addition result is clear (bit zero is cleared by the ISA).  A
            # dedicated two-bit carry avoids putting trap qualification behind
            # the full XLEN ALU adder.
            jalr_misaligned.next = \
                (bool(op1[1]) != bool(op2[1])) != \
                (bool(op1[0]) and bool(op2[0]))

        @always_comb
        def registered_trap_tval_comb():
            # Select MTVAL after each possible wide data source has crossed
            # the redirect-stage register boundary.  In particular, the ALU
            # carry chain no longer feeds the large exception-data mux before
            # reaching a register.
            registered_trap_tval.next = 0
            if trap_pending_cause == 0:
                if trap_pending_jalr:
                    registered_trap_tval.next = trap_pending_alu_tval
                else:
                    registered_trap_tval.next = trap_pending_jump_tval
            elif trap_pending_cause == 2:
                registered_trap_tval.next = trap_pending_instruction
            elif trap_pending_cause == 4 or trap_pending_cause == 5 or \
                    trap_pending_cause == 6 or trap_pending_cause == 7:
                registered_trap_tval.next = ls_fault_address

        @always_comb
        def debug_ebreak_comb():
            # Keep debug-entry qualification independent from the exception
            # classifier.  EBREAK-to-debug is not a machine trap, and folding
            # it into jump_comb made the complete CSR/exception cone feed the
            # debug controller's DPC write enable.
            debug_ebreak.next = self.taken and decode.sys_cmd and \
                decode.debug_word_o == 0x00100073 and debug_ebreak_enable
            debug_ebreak_pc.next = decode.mepc_o

        @always_comb
        def normal_redirect_comb():
            # The registered four-stage redirect path only needs the normal
            # control-flow decision and target.  Compute both independently
            # from machine-trap classification so illegal-opcode and CSR fault
            # logic cannot lengthen the redirect register input.
            take = False
            target = modbv(0)[self.config.xlen:]

            if decode.branch_cmd:
                if decode.funct3_o == b3.RV32_F3_BEQ:
                    take = bool(self.alu.flag_equal)
                elif decode.funct3_o == b3.RV32_F3_BGE:
                    take = bool(self.alu.flag_ge)
                elif decode.funct3_o == b3.RV32_F3_BGEU:
                    take = bool(self.alu.flag_uge)
                elif decode.funct3_o == b3.RV32_F3_BLT:
                    take = not bool(self.alu.flag_ge)
                elif decode.funct3_o == b3.RV32_F3_BLTU:
                    take = not bool(self.alu.flag_uge)
                elif decode.funct3_o == b3.RV32_F3_BNE:
                    take = not bool(self.alu.flag_equal)
                target[:] = decode.jump_dest_o
                if decode.jump_dest_o[self.config.ip_low:0] != 0:
                    take = False
            elif decode.jump_cmd:
                target[:] = decode.jump_dest_o
                take = decode.jump_dest_o[self.config.ip_low:0] == 0
            elif decode.jumpr_cmd:
                target[:] = self.alu.res_o
                target[0] = False
                take = not jalr_misaligned
            elif decode.sys_cmd and decode.debug_word_o == 0x30200073:
                target[:] = self.trapCSR.mepc << self.config.ip_low
                take = True

            normal_jump.next = take
            normal_jump_dest.next = target

        @always_comb
        def jump_comb():

            upper = self.config.xlen
            lower = self.config.ip_low

            do_jump = False
            jump_target = modbv(0)[self.config.xlen:]
            do_register_write = False
            fault = False
            fault_cause = 0
            fault_tval = modbv(0)[self.config.xlen:]
            fault_epc = modbv(0)[self.config.xlen:]
            fault_epc[:] = decode.mepc_o
            invalid_opcode = False

            if self.ls.valid_o and (
                self.ls.invalid_op_o or self.ls.misalign_load_o or
                self.ls.misalign_store_o or self.ls.bus_error_o
            ):
                fault = True
                fault_epc[:] = ls_fault_pc
                fault_tval[:] = ls_fault_address
                if self.ls.misalign_load_o:
                    fault_cause = 4
                elif self.ls.misalign_store_o:
                    fault_cause = 6
                elif ls_fault_store:
                    fault_cause = 7
                else:
                    fault_cause = 5

            elif self.taken:
                if decode.invalid_opcode:
                    fault = True
                    fault_cause = 2
                    fault_tval[:] = decode.debug_word_o
                    invalid_opcode = True

                elif decode.branch_cmd:
                    take_branch = False
                    f3 = decode.funct3_o
                    if f3==b3.RV32_F3_BEQ:
                        take_branch = bool(self.alu.flag_equal)
                    elif f3==b3.RV32_F3_BGE:
                        take_branch = bool(self.alu.flag_ge)
                    elif f3==b3.RV32_F3_BGEU:
                        take_branch = bool(self.alu.flag_uge)
                    elif f3==b3.RV32_F3_BLT:
                        take_branch = not bool(self.alu.flag_ge)
                    elif f3==b3.RV32_F3_BLTU:
                        take_branch = not bool(self.alu.flag_uge)
                    elif f3==b3.RV32_F3_BNE:
                        take_branch = not bool(self.alu.flag_equal)
                    else:
                        fault = True
                        fault_cause = 2
                        fault_tval[:] = decode.debug_word_o
                        invalid_opcode = True

                    if take_branch:
                        jump_target[:] = decode.jump_dest_o
                        if decode.jump_dest_o[lower:0] != 0:
                            fault = True
                            fault_cause = 0
                            fault_tval[:] = jump_target
                        else:
                            do_jump = True

                elif decode.jump_cmd:
                    jump_target[:] = decode.jump_dest_o
                    if decode.jump_dest_o[lower:0] != 0:
                        fault = True
                        fault_cause = 0
                        fault_tval[:] = jump_target
                    else:
                        do_jump = True
                        do_register_write = True

                elif decode.jumpr_cmd:
                    jump_target[:] = self.alu.res_o
                    jump_target[0] = False
                    # Bit zero is cleared architecturally by JALR.  Test only
                    # the remaining alignment bits directly so trap_valid does
                    # not inherit the full redirect-data mux and adder cone.
                    if jalr_misaligned:
                        fault = True
                        fault_cause = 0
                        fault_tval[:] = jump_target
                    else:
                        do_jump = True
                        do_register_write = True

                elif decode.load_cmd or decode.store_cmd:
                    if ls_issue_invalid:
                        fault = True
                        fault_cause = 2
                        fault_tval[:] = decode.debug_word_o
                        invalid_opcode = True
                    elif ls_issue_misaligned:
                        fault = True
                        fault_tval[:] = ls_effective_address
                        if decode.store_cmd:
                            fault_cause = 6
                        else:
                            fault_cause = 4

                elif decode.csr_cmd and self.csr.invalid_op_o:
                    fault = True
                    fault_cause = 2
                    fault_tval[:] = decode.debug_word_o
                    invalid_opcode = True

                elif decode.sys_cmd:
                    instruction = decode.debug_word_o
                    if instruction == 0x00100073 and debug_ebreak_enable:
                        pass
                    elif instruction == 0x00000073:
                        fault = True
                        fault_cause = 11
                    elif instruction == 0x00100073:
                        fault = True
                        fault_cause = 3
                    elif instruction == 0x30200073:
                        do_jump = True
                        jump_target[:] = self.trapCSR.mepc << lower
                    else:
                        fault = True
                        fault_cause = 2
                        fault_tval[:] = instruction
                        invalid_opcode = True

            if fault:
                do_register_write = False
                if self.config.jump_bypass and not debug_progbuf_active:
                    do_jump = True
                    jump_target[:] = self.trapCSR.mtvec << lower

            trap_valid.next = fault
            trap_cause.next = fault_cause
            trap_epc.next = fault_epc
            trap_tval.next = fault_tval
            self.invalid_opcode_fault.next = invalid_opcode
            jump.next = do_jump
            jump_dest.next = jump_target
            jump_we.next = do_register_write
            if self.config.jump_bypass:
                self.redirect_o.next = do_jump
            else:
                self.redirect_o.next = normal_jump or \
                    (trap_pending and not trap_pending_progbuf)
            if not self.config.jump_bypass and trap_pending:
                self.next_pc_o.next = self.trapCSR.mtvec << lower
            elif do_jump:
                self.next_pc_o.next = jump_target
            else:
                self.next_pc_o.next = decode.next_ip_o

            self.trap_request.is_interrupt.next = False
            if self.config.jump_bypass:
                self.trap_request.valid.next = fault
                self.trap_request.cause.next = fault_cause
                self.trap_request.epc.next = fault_epc
                self.trap_request.tval.next = fault_tval
                if debug_progbuf_active:
                    self.trap_request.source.next = \
                        PIPELINE_SOURCE_PROGRAM_BUFFER
                else:
                    self.trap_request.source.next = PIPELINE_SOURCE_NORMAL
                self.trap_request.ack.next = fault

                self.csrUpdate.mstatus_trap_enter.next = \
                    fault and not debug_progbuf_active
                self.csrUpdate.we_mcause.next = \
                    fault and not debug_progbuf_active
                self.csrUpdate.we_mtval.next = \
                    fault and not debug_progbuf_active
                self.csrUpdate.mtval.next = fault_tval
                self.csrUpdate.mepc.next = fault_epc[upper:lower]
                self.csrUpdate.we_mepc.next = \
                    fault and not debug_progbuf_active
            else:
                self.trap_request.valid.next = trap_pending
                self.trap_request.cause.next = trap_pending_cause
                self.trap_request.epc.next = trap_pending_epc
                self.trap_request.tval.next = registered_trap_tval
                if trap_pending_progbuf:
                    self.trap_request.source.next = \
                        PIPELINE_SOURCE_PROGRAM_BUFFER
                else:
                    self.trap_request.source.next = PIPELINE_SOURCE_NORMAL
                self.trap_request.ack.next = trap_pending

                self.csrUpdate.mstatus_trap_enter.next = \
                    trap_pending and not trap_pending_progbuf
                self.csrUpdate.we_mcause.next = \
                    trap_pending and not trap_pending_progbuf
                self.csrUpdate.we_mtval.next = \
                    trap_pending and not trap_pending_progbuf
                self.csrUpdate.mtval.next = registered_trap_tval
                self.csrUpdate.mepc.next = trap_pending_epc[upper:lower]
                self.csrUpdate.we_mepc.next = \
                    trap_pending and not trap_pending_progbuf

            self.csrUpdate.mstatus_trap_exit.next = self.taken and \
                decode.sys_cmd and decode.debug_word_o == 0x30200073

        @always_comb
        def retirement_event():
            control_retire.next = self.taken and not trap_valid and (
                decode.branch_cmd or decode.fence_cmd or
                (decode.sys_cmd and decode.debug_word_o == 0x30200073)
            )
            retire.next = valid or control_retire
            self.control_retire_o.next = control_retire

            #TODO: Implement other functional units


        return instances()

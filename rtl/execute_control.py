"""
Control-Flow and Synchronous-Exception Handling for Execute
(c) 2026 The Bonfire Project
License: See LICENSE

Control-flow and synchronous-exception handling for Execute.
"""

from myhdl import Signal, always_comb, always_seq, block, instances, modbv

from rtl.bonfire_interfaces import (
    PIPELINE_SOURCE_NORMAL,
    PIPELINE_SOURCE_PROGRAM_BUFFER,
)
from rtl.instructions import SystemOperation
from rtl.control_flow import ControlFlowBundle
from rtl.static_data_access import DataAccessFaultMode


CAUSE_INSTRUCTION_ADDRESS_MISALIGNED = 0
CAUSE_ILLEGAL_INSTRUCTION = 2
CAUSE_BREAKPOINT = 3
CAUSE_LOAD_ADDRESS_MISALIGNED = 4
CAUSE_LOAD_ACCESS_FAULT = 5
CAUSE_STORE_ADDRESS_MISALIGNED = 6
CAUSE_STORE_ACCESS_FAULT = 7
CAUSE_MACHINE_ECALL = 11


class ExecuteControlBundle:
    """Redirect, exception, and trap-update outputs consumed by Execute."""

    def __init__(self, config):
        xlen = config.xlen
        self.config = config

        self.jump_decision_o = Signal(bool(0))
        self.jump_write_o = Signal(bool(0))
        self.jump_o = Signal(bool(0))
        self.jump_dest_o = Signal(modbv(0)[xlen:])
        self.jump_busy_o = Signal(bool(0))
        self.redirect_o = Signal(bool(0))
        self.next_pc_o = Signal(modbv(0)[xlen:])

        self.trap_valid_o = Signal(bool(0))
        self.trap_pending_o = Signal(bool(0))
        self.trap_pending_progbuf_o = Signal(bool(0))
        self.invalid_opcode_fault_o = Signal(bool(0))
        self.jalr_misaligned_o = Signal(bool(0))
        self.control_retire_o = Signal(bool(0))

        self.debug_ebreak_o = Signal(bool(0))
        self.debug_ebreak_pc_o = Signal(modbv(0)[xlen:])

    @block
    def controller(
        self, decode, alu_result, alu_flag_equal, alu_flag_ge, alu_flag_uge,
        loadstore, csr_unit, trap_csrs, csr_update,
        trap_request,
        taken, clock, reset, debug_ebreak_enable,
        debug_progbuf_active,
    ):
        xlen = self.config.xlen
        lower = self.config.ip_low
        bus_response_faults = \
            self.config.data_access_fault_mode != DataAccessFaultMode.STATIC_MAP
        control_flow = ControlFlowBundle(self.config)
        control_flow_inst = control_flow.controller(
            decode.branch_cmd, decode.jump_cmd, decode.jumpr_cmd,
            decode.funct3_o, decode.jump_dest_o, alu_result,
            alu_flag_equal, alu_flag_ge, alu_flag_uge)

        jump_r = Signal(bool(0))
        jump_dest = Signal(modbv(0)[xlen:])
        jump_dest_r = Signal(modbv(0)[xlen:])
        normal_jump = Signal(bool(0))
        normal_jump_dest = Signal(modbv(0)[xlen:])
        # These signals are only driven and consumed in bus-response mode.
        # Keeping their declarations unconditional avoids empty closures in
        # MyHDL's static-map conversion; static elaborations contain no
        # registers or logic for them.
        ls_fault_address = Signal(modbv(0)[xlen:])
        ls_fault_pc = Signal(modbv(0)[xlen:])
        ls_fault_store = Signal(bool(0))

        trap_cause = Signal(modbv(0)[6:])
        trap_epc = Signal(modbv(0)[xlen:])
        trap_tval = Signal(modbv(0)[xlen:])
        trap_pending_cause = Signal(modbv(0)[6:])
        trap_pending_epc = Signal(modbv(0)[xlen:])
        trap_pending_tval = Signal(modbv(0)[xlen:])

        @always_seq(clock.posedge, reset=reset)
        def state():
            self.jump_busy_o.next = False
            self.trap_pending_o.next = False
            trap_pending_cause.next = trap_cause
            trap_pending_epc.next = trap_epc
            trap_pending_tval.next = trap_tval
            self.trap_pending_progbuf_o.next = debug_progbuf_active

            if self.trap_valid_o:
                self.trap_pending_o.next = True

            if self.config.jump_bypass:
                if self.trap_valid_o:
                    jump_dest_r.next = jump_dest
                    jump_r.next = self.jump_decision_o
                elif taken:
                    jump_dest_r.next = jump_dest
                    jump_r.next = self.jump_decision_o
            elif taken:
                # Keep the normal redirect register independent from the
                # exception classifier and its metadata muxes.
                jump_dest_r.next = normal_jump_dest
                jump_r.next = normal_jump
                self.jump_busy_o.next = normal_jump

            if bus_response_faults:
                if taken and (decode.load_cmd or decode.store_cmd):
                    ls_fault_address.next = loadstore.issue.effective_address_o

                if loadstore.taken:
                    ls_fault_pc.next = decode.mepc_o
                    ls_fault_store.next = decode.store_cmd

        @always_comb
        def control_flow_status():
            self.jalr_misaligned_o.next = \
                decode.jumpr_cmd and control_flow.misaligned_o

        @always_comb
        def debug_ebreak_comb():
            self.debug_ebreak_o.next = taken and decode.sys_cmd and \
                decode.system_operation_o == SystemOperation.EBREAK and \
                debug_ebreak_enable
            self.debug_ebreak_pc_o.next = decode.mepc_o

        @always_comb
        def normal_redirect_comb():
            normal_jump.next = control_flow.redirect_o
            normal_jump_dest.next = control_flow.target_o
            if decode.sys_cmd and \
                    decode.system_operation_o == SystemOperation.MRET:
                normal_jump.next = True
                normal_jump_dest.next = trap_csrs.mepc << lower

        @always_comb
        def exception_classifier():
            do_jump = False
            jump_target = modbv(0)[xlen:]
            do_register_write = False
            fault = False
            fault_cause = 0
            fault_tval = modbv(0)[xlen:]
            fault_epc = modbv(0)[xlen:]
            fault_epc[:] = decode.mepc_o
            invalid_opcode = False

            if bus_response_faults and loadstore.valid_o and (
                loadstore.invalid_op_o or loadstore.misalign_load_o or
                loadstore.misalign_store_o or loadstore.bus_error_o
            ):
                fault = True
                fault_epc[:] = ls_fault_pc
                fault_tval[:] = ls_fault_address
                if loadstore.misalign_load_o:
                    fault_cause = CAUSE_LOAD_ADDRESS_MISALIGNED
                elif loadstore.misalign_store_o:
                    fault_cause = CAUSE_STORE_ADDRESS_MISALIGNED
                elif ls_fault_store:
                    fault_cause = CAUSE_STORE_ACCESS_FAULT
                else:
                    fault_cause = CAUSE_LOAD_ACCESS_FAULT

            elif taken:
                if decode.invalid_opcode:
                    fault = True
                    fault_cause = CAUSE_ILLEGAL_INSTRUCTION
                    fault_tval[:] = decode.debug_word_o
                    invalid_opcode = True
                elif decode.branch_cmd or decode.jump_cmd or decode.jumpr_cmd:
                    jump_target[:] = control_flow.target_o
                    if control_flow.misaligned_o:
                        fault = True
                        fault_cause = CAUSE_INSTRUCTION_ADDRESS_MISALIGNED
                        fault_tval[:] = control_flow.tval_o
                    else:
                        do_jump = bool(control_flow.redirect_o)
                        do_register_write = bool(control_flow.link_write_o)
                elif decode.load_cmd or decode.store_cmd:
                    if loadstore.issue.invalid_o:
                        fault = True
                        fault_cause = CAUSE_ILLEGAL_INSTRUCTION
                        fault_tval[:] = decode.debug_word_o
                        invalid_opcode = True
                    elif loadstore.issue.misaligned_o:
                        fault = True
                        fault_tval[:] = loadstore.issue.effective_address_o
                        if decode.store_cmd:
                            fault_cause = CAUSE_STORE_ADDRESS_MISALIGNED
                        else:
                            fault_cause = CAUSE_LOAD_ADDRESS_MISALIGNED
                    elif loadstore.issue.access_fault_o:
                        fault = True
                        fault_tval[:] = loadstore.issue.effective_address_o
                        if decode.store_cmd:
                            fault_cause = CAUSE_STORE_ACCESS_FAULT
                        else:
                            fault_cause = CAUSE_LOAD_ACCESS_FAULT
                elif decode.csr_cmd and csr_unit.invalid_op_o:
                    fault = True
                    fault_cause = CAUSE_ILLEGAL_INSTRUCTION
                    fault_tval[:] = decode.debug_word_o
                    invalid_opcode = True
                elif decode.sys_cmd:
                    system_operation = decode.system_operation_o
                    if system_operation == SystemOperation.EBREAK and \
                            debug_ebreak_enable:
                        pass
                    elif system_operation == SystemOperation.ECALL:
                        fault = True
                        fault_cause = CAUSE_MACHINE_ECALL
                    elif system_operation == SystemOperation.EBREAK:
                        fault = True
                        fault_cause = CAUSE_BREAKPOINT
                    elif system_operation == SystemOperation.MRET:
                        do_jump = True
                        jump_target[:] = trap_csrs.mepc << lower
                    else:
                        fault = True
                        fault_cause = CAUSE_ILLEGAL_INSTRUCTION
                        fault_tval[:] = decode.debug_word_o
                        invalid_opcode = True

            if fault:
                do_register_write = False
                if self.config.jump_bypass and not debug_progbuf_active:
                    do_jump = True
                    jump_target[:] = trap_csrs.mtvec << lower

            self.trap_valid_o.next = fault
            trap_cause.next = fault_cause
            trap_epc.next = fault_epc
            trap_tval.next = fault_tval
            self.invalid_opcode_fault_o.next = invalid_opcode
            self.jump_decision_o.next = do_jump
            jump_dest.next = jump_target
            self.jump_write_o.next = do_register_write
            if self.config.jump_bypass:
                self.redirect_o.next = do_jump
            else:
                self.redirect_o.next = normal_jump or \
                    (self.trap_pending_o and
                     not self.trap_pending_progbuf_o)
            if not self.config.jump_bypass and self.trap_pending_o:
                self.next_pc_o.next = trap_csrs.mtvec << lower
            elif do_jump:
                self.next_pc_o.next = jump_target
            else:
                self.next_pc_o.next = decode.next_ip_o

            commit_valid = False
            commit_cause = 0
            commit_epc = modbv(0)[xlen:]
            commit_tval = modbv(0)[xlen:]
            commit_progbuf = False
            if self.config.jump_bypass:
                commit_valid = fault
                commit_cause = fault_cause
                commit_epc[:] = fault_epc
                commit_tval[:] = fault_tval
                commit_progbuf = bool(debug_progbuf_active)
            else:
                commit_valid = bool(self.trap_pending_o)
                commit_cause = int(trap_pending_cause)
                commit_epc[:] = trap_pending_epc
                commit_tval[:] = trap_pending_tval
                commit_progbuf = bool(self.trap_pending_progbuf_o)

            trap_request.is_interrupt.next = False
            trap_request.valid.next = commit_valid
            trap_request.cause.next = commit_cause
            trap_request.epc.next = commit_epc
            trap_request.tval.next = commit_tval
            if commit_progbuf:
                trap_request.source.next = PIPELINE_SOURCE_PROGRAM_BUFFER
            else:
                trap_request.source.next = PIPELINE_SOURCE_NORMAL
            trap_request.ack.next = commit_valid

            commit_machine_trap = commit_valid and not commit_progbuf
            csr_update.mstatus_trap_enter.next = commit_machine_trap
            csr_update.we_mcause.next = commit_machine_trap
            csr_update.we_mtval.next = commit_machine_trap
            csr_update.mtval.next = commit_tval
            csr_update.mepc.next = commit_epc[xlen:lower]
            csr_update.we_mepc.next = commit_machine_trap
            csr_update.mstatus_trap_exit.next = taken and decode.sys_cmd and \
                decode.system_operation_o == SystemOperation.MRET

        @always_comb
        def mcause_update():
            csr_update.mcause_irq.next = 0
            if self.config.jump_bypass:
                csr_update.mcause.next = trap_cause
            else:
                csr_update.mcause.next = trap_pending_cause

        @always_comb
        def redirect_output():
            if self.trap_valid_o and self.config.jump_bypass:
                self.jump_o.next = self.jump_decision_o
                self.jump_dest_o.next = jump_dest
            elif taken and self.config.jump_bypass:
                self.jump_o.next = self.jump_decision_o
                self.jump_dest_o.next = jump_dest
            elif self.trap_pending_o and not self.config.jump_bypass:
                self.jump_o.next = not self.trap_pending_progbuf_o
                self.jump_dest_o.next = trap_csrs.mtvec << lower
            else:
                self.jump_o.next = jump_r and not taken
                self.jump_dest_o.next = jump_dest_r

        @always_comb
        def retirement_control():
            self.control_retire_o.next = taken and \
                not self.trap_valid_o and (
                    decode.branch_cmd or decode.fence_cmd or
                    (decode.sys_cmd and
                     decode.system_operation_o == SystemOperation.MRET)
                )

        return instances()

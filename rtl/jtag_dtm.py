"""
JTAG Debug Transport Module for the Bonfire debug module.

This implements a small RISC-V debug compatible TAP with IDCODE, DTMCS, DMI
and BYPASS instructions. The DMI scan register drives the existing
AbstractDebugTransportBundle used by rtl.debugModule.DMI.
"""
from __future__ import annotations

from typing import Any

from myhdl import *
from rtl.debugModule import AbstractDebugTransportBundle
from rtl.type_aliases import BitSignal


JTAG_IR_WIDTH = 5

JTAG_INSTR_IDCODE = 0x01
JTAG_INSTR_DTMCS = 0x10
JTAG_INSTR_DMI = 0x11
JTAG_INSTR_BYPASS = 0x1F

JTAG_IDCODE = 0x10E31913

DTM_VERSION = 1
DTM_IDLE = 1

DMI_OP_NOP = 0
DMI_OP_READ = 1
DMI_OP_WRITE = 2
DMI_OP_SUCCESS = 0

t_tapState = enum(
    'test_logic_reset',
    'run_test_idle',
    'select_dr_scan',
    'capture_dr',
    'shift_dr',
    'exit1_dr',
    'pause_dr',
    'exit2_dr',
    'update_dr',
    'select_ir_scan',
    'capture_ir',
    'shift_ir',
    'exit1_ir',
    'pause_ir',
    'exit2_ir',
    'update_ir',
)


class JtagDTM:
    def __init__(self, config: Any) -> None:
        self.config = config
        self.abits: int = config.dmi_adr_width
        self.dmi_width: int = self.abits + 34

    @block
    def createInstance(
        self,
        tck: BitSignal,
        trst: BitSignal,
        tms: BitSignal,
        tdi: BitSignal,
        tdo: BitSignal,
        dtm: AbstractDebugTransportBundle,
    ) -> Any:
        """Create a JTAG DTM instance.

        The DMI scan layout is compatible with the RISC-V debug spec:
        ``{address, data, op}``, shifted least-significant bit first.
        """

        abits = self.abits
        dmi_width = self.dmi_width
        dr_width = dmi_width

        tap_state = Signal(t_tapState.test_logic_reset)
        instruction = Signal(modbv(JTAG_INSTR_IDCODE)[JTAG_IR_WIDTH:])
        ir_shift = Signal(modbv(0)[JTAG_IR_WIDTH:])
        dr_shift = Signal(modbv(0)[dr_width:])
        dmi_response = Signal(modbv(0)[dmi_width:])
        bypass = Signal(bool(0))
        dmi_request_active = Signal(bool(0))
        dmi_read_pending = Signal(bool(0))
        dmi_read_capture = Signal(bool(0))

        @always_comb
        def tdo_select():
            if tap_state == t_tapState.shift_ir:
                tdo.next = ir_shift[0]
            elif tap_state == t_tapState.shift_dr:
                if instruction == JTAG_INSTR_BYPASS:
                    tdo.next = bypass
                else:
                    tdo.next = dr_shift[0]
            else:
                tdo.next = False

        @always_seq(tck.posedge, reset=trst)
        def tap_state_transition():
            if tap_state == t_tapState.test_logic_reset:
                if tms:
                    tap_state.next = t_tapState.test_logic_reset
                else:
                    tap_state.next = t_tapState.run_test_idle
            elif tap_state == t_tapState.run_test_idle:
                if tms:
                    tap_state.next = t_tapState.select_dr_scan
                else:
                    tap_state.next = t_tapState.run_test_idle
            elif tap_state == t_tapState.select_dr_scan:
                if tms:
                    tap_state.next = t_tapState.select_ir_scan
                else:
                    tap_state.next = t_tapState.capture_dr
            elif tap_state == t_tapState.capture_dr:
                if tms:
                    tap_state.next = t_tapState.exit1_dr
                else:
                    tap_state.next = t_tapState.shift_dr
            elif tap_state == t_tapState.shift_dr:
                if tms:
                    tap_state.next = t_tapState.exit1_dr
                else:
                    tap_state.next = t_tapState.shift_dr
            elif tap_state == t_tapState.exit1_dr:
                if tms:
                    tap_state.next = t_tapState.update_dr
                else:
                    tap_state.next = t_tapState.pause_dr
            elif tap_state == t_tapState.pause_dr:
                if tms:
                    tap_state.next = t_tapState.exit2_dr
                else:
                    tap_state.next = t_tapState.pause_dr
            elif tap_state == t_tapState.exit2_dr:
                if tms:
                    tap_state.next = t_tapState.update_dr
                else:
                    tap_state.next = t_tapState.shift_dr
            elif tap_state == t_tapState.update_dr:
                if tms:
                    tap_state.next = t_tapState.select_dr_scan
                else:
                    tap_state.next = t_tapState.run_test_idle
            elif tap_state == t_tapState.select_ir_scan:
                if tms:
                    tap_state.next = t_tapState.test_logic_reset
                else:
                    tap_state.next = t_tapState.capture_ir
            elif tap_state == t_tapState.capture_ir:
                if tms:
                    tap_state.next = t_tapState.exit1_ir
                else:
                    tap_state.next = t_tapState.shift_ir
            elif tap_state == t_tapState.shift_ir:
                if tms:
                    tap_state.next = t_tapState.exit1_ir
                else:
                    tap_state.next = t_tapState.shift_ir
            elif tap_state == t_tapState.exit1_ir:
                if tms:
                    tap_state.next = t_tapState.update_ir
                else:
                    tap_state.next = t_tapState.pause_ir
            elif tap_state == t_tapState.pause_ir:
                if tms:
                    tap_state.next = t_tapState.exit2_ir
                else:
                    tap_state.next = t_tapState.pause_ir
            elif tap_state == t_tapState.exit2_ir:
                if tms:
                    tap_state.next = t_tapState.update_ir
                else:
                    tap_state.next = t_tapState.shift_ir
            else:
                if tms:
                    tap_state.next = t_tapState.select_dr_scan
                else:
                    tap_state.next = t_tapState.run_test_idle

        @always_seq(tck.posedge, reset=trst)
        def tap_actions():
            if dmi_request_active:
                dtm.en.next = False
                dmi_request_active.next = False
                if dmi_read_pending:
                    dmi_read_pending.next = False
                    dmi_read_capture.next = True

            if dmi_read_capture:
                dmi_response.next[2:0] = DMI_OP_SUCCESS
                dmi_response.next[34:2] = dtm.dbo
                dmi_read_capture.next = False

            if tap_state == t_tapState.test_logic_reset and tms:
                instruction.next = JTAG_INSTR_IDCODE

            if tap_state == t_tapState.capture_ir:
                ir_shift.next = 0x01
            elif tap_state == t_tapState.shift_ir:
                ir_shift.next[JTAG_IR_WIDTH - 1] = tdi
                ir_shift.next[JTAG_IR_WIDTH - 1:0] = ir_shift[JTAG_IR_WIDTH:1]
            elif tap_state == t_tapState.update_ir:
                instruction.next = ir_shift

            if tap_state == t_tapState.capture_dr:
                if instruction == JTAG_INSTR_IDCODE:
                    dr_shift.next = JTAG_IDCODE
                elif instruction == JTAG_INSTR_DTMCS:
                    dtmcs = modbv(0)[32:]
                    dtmcs[3:0] = DTM_VERSION
                    dtmcs[9:4] = abits
                    dtmcs[12:10] = DTM_IDLE
                    dr_shift.next = dtmcs
                elif instruction == JTAG_INSTR_DMI:
                    dr_shift.next = dmi_response
                elif instruction == JTAG_INSTR_BYPASS:
                    bypass.next = False
                else:
                    bypass.next = False
            elif tap_state == t_tapState.shift_dr:
                if instruction == JTAG_INSTR_BYPASS:
                    bypass.next = tdi
                else:
                    dr_shift.next[dr_width - 1] = tdi
                    dr_shift.next[dr_width - 1:0] = dr_shift[dr_width:1]
            elif tap_state == t_tapState.update_dr:
                if instruction == JTAG_INSTR_DMI:
                    op = dr_shift[2:0]
                    dtm.adr.next = dr_shift[dmi_width:34]
                    dtm.dbi.next = dr_shift[34:2]

                    if op == DMI_OP_READ:
                        dtm.we.next = False
                        dtm.en.next = True
                        dmi_request_active.next = True
                        dmi_read_pending.next = True
                        dmi_response.next[2:0] = DMI_OP_SUCCESS
                        dmi_response.next[34:2] = 0
                        dmi_response.next[dmi_width:34] = dr_shift[dmi_width:34]
                    elif op == DMI_OP_WRITE:
                        dtm.we.next = True
                        dtm.en.next = True
                        dmi_request_active.next = True
                        dmi_response.next[2:0] = DMI_OP_SUCCESS
                        dmi_response.next[34:2] = 0
                        dmi_response.next[dmi_width:34] = dr_shift[dmi_width:34]
                    else:
                        dmi_response.next[2:0] = DMI_OP_SUCCESS

        return instances()

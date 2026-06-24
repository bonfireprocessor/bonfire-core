"""
JTAG Debug Transport Module for the Bonfire debug module.
(c) 2026 The Bonfire Project
License: See LICENSE

This implements a small RISC-V debug compatible TAP with IDCODE, DTMCS, DMI
and BYPASS instructions. The DMI scan register drives the DmiBundle consumed
by the Debug Module Interface.
"""
from __future__ import annotations

from typing import Any

from myhdl import *
from rtl.debug import DmiBundle
from rtl.type_aliases import BitSignal


JTAG_IR_WIDTH = 5

JTAG_INSTR_IDCODE = 0x01
JTAG_INSTR_DTMCS = 0x10
JTAG_INSTR_DMI = 0x11
JTAG_INSTR_BYPASS = 0x1F
JTAG_INSTR_ECP5_ER1_DMI = 0x32
JTAG_INSTR_ECP5_ER2_DTMCS = 0x38

JTAG_IDCODE = 0x10E31913

DTM_VERSION = 1
DTM_IDLE = 1
DTM_DMI_STATUS_OK = 0
DTMCS_DMIRESET_BIT = 16

DMI_OP_NOP = 0
DMI_OP_READ = 1
DMI_OP_WRITE = 2
DMI_OP_SUCCESS = 0

t_tap_state = enum(
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
        self.ir_width: int = getattr(config, "debug_jtag_ir_width", JTAG_IR_WIDTH)
        self.ir_idcode: int = getattr(config, "debug_jtag_ir_idcode", JTAG_INSTR_IDCODE)
        self.ir_dtmcs: int = getattr(config, "debug_jtag_ir_dtmcs", JTAG_INSTR_DTMCS)
        self.ir_dmi: int = getattr(config, "debug_jtag_ir_dmi", JTAG_INSTR_DMI)
        self.ir_bypass: int = getattr(config, "debug_jtag_ir_bypass", JTAG_INSTR_BYPASS)

    @block
    def createInstance(
        self,
        clock: BitSignal,
        reset: BitSignal,
        tck_i: BitSignal,
        tms_i: BitSignal,
        tdi_i: BitSignal,
        trstn_i: BitSignal,
        tdo_o: BitSignal,
        dtm: DmiBundle,
        tap_state_o: Any = None,
    ) -> Any:
        """Create a JTAG DTM instance.

        The DMI scan layout is compatible with the RISC-V debug spec:
        ``{address, data, op}``, shifted least-significant bit first.
        """

        abits = self.abits
        dmi_width = self.dmi_width
        dr_width = dmi_width

        tap_state = Signal(t_tap_state.test_logic_reset)
        instruction = Signal(modbv(self.ir_idcode)[self.ir_width:])
        ir_shift = Signal(modbv(0)[self.ir_width:])
        dr_shift = Signal(modbv(0)[dr_width:])
        dmi_response = Signal(modbv(0)[dmi_width:])
        bypass = Signal(bool(0))
        dmi_request_active = Signal(bool(0))
        dmi_read_pending = Signal(bool(0))
        dmi_read_capture = Signal(bool(0))
        dmistat = Signal(modbv(DTM_DMI_STATUS_OK)[2:])

        tck_meta = Signal(bool(0))
        tck_sync = Signal(bool(0))
        tck_sync_d = Signal(bool(0))
        tms_meta = Signal(bool(1))
        tms_sync = Signal(bool(1))
        tdi_meta = Signal(bool(0))
        tdi_sync = Signal(bool(0))
        trstn_meta = Signal(bool(1))
        trstn_sync = Signal(bool(1))
        tck_rise = Signal(bool(0))
        tck_fall = Signal(bool(0))

        @always_seq(clock.posedge, reset=reset)
        def jtag_input_sync():
            tck_meta.next = tck_i
            tck_sync.next = tck_meta
            tck_sync_d.next = tck_sync
            tms_meta.next = tms_i
            tms_sync.next = tms_meta
            tdi_meta.next = tdi_i
            tdi_sync.next = tdi_meta
            trstn_meta.next = trstn_i
            trstn_sync.next = trstn_meta

        @always_comb
        def tck_edge_detect():
            tck_rise.next = tck_sync and not tck_sync_d
            tck_fall.next = not tck_sync and tck_sync_d

        @always_seq(clock.posedge, reset=reset)
        def tdo_select():
            if not trstn_sync:
                tdo_o.next = False
            elif tck_fall:
                if tap_state == t_tap_state.shift_ir:
                    tdo_o.next = ir_shift[0]
                elif tap_state == t_tap_state.shift_dr:
                    if instruction == self.ir_bypass:
                        tdo_o.next = bypass
                    else:
                        tdo_o.next = dr_shift[0]
                else:
                    tdo_o.next = False

        if tap_state_o is not None:
            @always_comb
            def tap_state_observe():
                tap_state_o.next = tap_state

        @always_seq(clock.posedge, reset=reset)
        def tap_state_transition():
            if not trstn_sync:
                tap_state.next = t_tap_state.test_logic_reset
            elif tck_rise:
                if tap_state == t_tap_state.test_logic_reset:
                    if tms_sync:
                        tap_state.next = t_tap_state.test_logic_reset
                    else:
                        tap_state.next = t_tap_state.run_test_idle
                elif tap_state == t_tap_state.run_test_idle:
                    if tms_sync:
                        tap_state.next = t_tap_state.select_dr_scan
                    else:
                        tap_state.next = t_tap_state.run_test_idle
                elif tap_state == t_tap_state.select_dr_scan:
                    if tms_sync:
                        tap_state.next = t_tap_state.select_ir_scan
                    else:
                        tap_state.next = t_tap_state.capture_dr
                elif tap_state == t_tap_state.capture_dr:
                    if tms_sync:
                        tap_state.next = t_tap_state.exit1_dr
                    else:
                        tap_state.next = t_tap_state.shift_dr
                elif tap_state == t_tap_state.shift_dr:
                    if tms_sync:
                        tap_state.next = t_tap_state.exit1_dr
                    else:
                        tap_state.next = t_tap_state.shift_dr
                elif tap_state == t_tap_state.exit1_dr:
                    if tms_sync:
                        tap_state.next = t_tap_state.update_dr
                    else:
                        tap_state.next = t_tap_state.pause_dr
                elif tap_state == t_tap_state.pause_dr:
                    if tms_sync:
                        tap_state.next = t_tap_state.exit2_dr
                    else:
                        tap_state.next = t_tap_state.pause_dr
                elif tap_state == t_tap_state.exit2_dr:
                    if tms_sync:
                        tap_state.next = t_tap_state.update_dr
                    else:
                        tap_state.next = t_tap_state.shift_dr
                elif tap_state == t_tap_state.update_dr:
                    if tms_sync:
                        tap_state.next = t_tap_state.select_dr_scan
                    else:
                        tap_state.next = t_tap_state.run_test_idle
                elif tap_state == t_tap_state.select_ir_scan:
                    if tms_sync:
                        tap_state.next = t_tap_state.test_logic_reset
                    else:
                        tap_state.next = t_tap_state.capture_ir
                elif tap_state == t_tap_state.capture_ir:
                    if tms_sync:
                        tap_state.next = t_tap_state.exit1_ir
                    else:
                        tap_state.next = t_tap_state.shift_ir
                elif tap_state == t_tap_state.shift_ir:
                    if tms_sync:
                        tap_state.next = t_tap_state.exit1_ir
                    else:
                        tap_state.next = t_tap_state.shift_ir
                elif tap_state == t_tap_state.exit1_ir:
                    if tms_sync:
                        tap_state.next = t_tap_state.update_ir
                    else:
                        tap_state.next = t_tap_state.pause_ir
                elif tap_state == t_tap_state.pause_ir:
                    if tms_sync:
                        tap_state.next = t_tap_state.exit2_ir
                    else:
                        tap_state.next = t_tap_state.pause_ir
                elif tap_state == t_tap_state.exit2_ir:
                    if tms_sync:
                        tap_state.next = t_tap_state.update_ir
                    else:
                        tap_state.next = t_tap_state.shift_ir
                else:
                    if tms_sync:
                        tap_state.next = t_tap_state.select_dr_scan
                    else:
                        tap_state.next = t_tap_state.run_test_idle

        @always_seq(clock.posedge, reset=reset)
        def tap_actions():
            if not trstn_sync:
                instruction.next = self.ir_idcode
                ir_shift.next = 0
                dr_shift.next = 0
                dmi_response.next = 0
                bypass.next = False
                dtm.en.next = False
                dtm.we.next = False
                dmi_request_active.next = False
                dmi_read_pending.next = False
                dmi_read_capture.next = False
                dmistat.next = DTM_DMI_STATUS_OK
            elif dmi_request_active:
                dtm.en.next = False
                dmi_request_active.next = False
                if dmi_read_pending:
                    dmi_read_pending.next = False
                    dmi_read_capture.next = True

            elif dmi_read_capture:
                dmi_response.next[2:0] = DMI_OP_SUCCESS
                dmi_response.next[34:2] = dtm.dbo
                dmi_read_capture.next = False

            if trstn_sync and tck_rise:
                if tap_state == t_tap_state.test_logic_reset and tms_sync:
                    instruction.next = self.ir_idcode

                if tap_state == t_tap_state.capture_ir:
                    ir_shift.next = 0x01
                elif tap_state == t_tap_state.shift_ir:
                    ir_shift.next[self.ir_width - 1] = tdi_sync
                    ir_shift.next[self.ir_width - 1:0] = ir_shift[self.ir_width:1]
                elif tap_state == t_tap_state.update_ir:
                    instruction.next = ir_shift

                if tap_state == t_tap_state.capture_dr:
                    if instruction == self.ir_idcode:
                        dr_shift.next = JTAG_IDCODE
                    elif instruction == self.ir_dtmcs:
                        dtmcs = modbv(0)[32:]
                        dtmcs[3:0] = DTM_VERSION
                        dtmcs[9:4] = abits
                        dtmcs[12:10] = dmistat
                        dtmcs[15:12] = DTM_IDLE
                        dr_shift.next = dtmcs
                    elif instruction == self.ir_dmi:
                        dr_shift.next = dmi_response
                    elif instruction == self.ir_bypass:
                        bypass.next = False
                    else:
                        bypass.next = False
                elif tap_state == t_tap_state.shift_dr:
                    if instruction == self.ir_bypass:
                        bypass.next = tdi_sync
                    elif instruction == self.ir_idcode or instruction == self.ir_dtmcs:
                        dr_shift.next[31] = tdi_sync
                        dr_shift.next[31:0] = dr_shift[32:1]
                    else:
                        dr_shift.next[dr_width - 1] = tdi_sync
                        dr_shift.next[dr_width - 1:0] = dr_shift[dr_width:1]
                elif tap_state == t_tap_state.update_dr:
                    if instruction == self.ir_dtmcs:
                        if dr_shift[DTMCS_DMIRESET_BIT]:
                            dmistat.next = DTM_DMI_STATUS_OK

                    if instruction == self.ir_dmi:
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

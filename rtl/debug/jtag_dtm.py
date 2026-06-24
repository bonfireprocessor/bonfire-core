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

from myhdl import Signal, always_comb, always_seq, block, enum, instances, modbv

from rtl.debug.dm_registers import DmiBundle
from rtl.debug.dtm_transport import DmiScanRegister, DtmcsScanRegister
from rtl.type_aliases import BitSignal


JTAG_IR_WIDTH = 5

JTAG_INSTR_IDCODE = 0x01
JTAG_INSTR_DTMCS = 0x10
JTAG_INSTR_DMI = 0x11
JTAG_INSTR_BYPASS = 0x1F

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
        tap_state = Signal(t_tap_state.test_logic_reset)
        instruction = Signal(modbv(JTAG_INSTR_IDCODE)[JTAG_IR_WIDTH:])
        ir_shift = Signal(modbv(0)[JTAG_IR_WIDTH:])
        idcode_shift = Signal(modbv(0)[32:])
        bypass = Signal(bool(0))

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

        dmi_capture = Signal(bool(0))
        dmi_shift = Signal(bool(0))
        dmi_update = Signal(bool(0))
        dtmcs_capture = Signal(bool(0))
        dtmcs_shift = Signal(bool(0))
        dtmcs_update = Signal(bool(0))
        dmi_tdo = Signal(bool(0))
        dtmcs_tdo = Signal(bool(0))
        dmistat = Signal(modbv(DTM_DMI_STATUS_OK)[2:])
        dmireset_pulse = Signal(bool(0))
        dmi_selected = Signal(bool(0))
        dtmcs_selected = Signal(bool(0))

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

        @always_comb
        def select_decode():
            dmi_selected.next = instruction == JTAG_INSTR_DMI
            dtmcs_selected.next = instruction == JTAG_INSTR_DTMCS

        @always_seq(clock.posedge, reset=reset)
        def drive_scan_controls():
            dmi_capture.next = False
            dmi_shift.next = False
            dmi_update.next = False
            dtmcs_capture.next = False
            dtmcs_shift.next = False
            dtmcs_update.next = False

            if tck_rise and trstn_sync:
                if tap_state == t_tap_state.capture_dr:
                    if dmi_selected:
                        dmi_capture.next = True
                    elif dtmcs_selected:
                        dtmcs_capture.next = True
                elif tap_state == t_tap_state.shift_dr:
                    if dmi_selected:
                        dmi_shift.next = True
                    elif dtmcs_selected:
                        dtmcs_shift.next = True
                elif tap_state == t_tap_state.update_dr:
                    if dmi_selected:
                        dmi_update.next = True
                    elif dtmcs_selected:
                        dtmcs_update.next = True

        @always_seq(clock.posedge, reset=reset)
        def tdo_select():
            if not trstn_sync:
                tdo_o.next = False
            elif tck_fall:
                if tap_state == t_tap_state.shift_ir:
                    tdo_o.next = ir_shift[0]
                elif tap_state == t_tap_state.shift_dr:
                    if instruction == JTAG_INSTR_BYPASS:
                        tdo_o.next = bypass
                    elif instruction == JTAG_INSTR_IDCODE:
                        tdo_o.next = idcode_shift[0]
                    elif dmi_selected:
                        tdo_o.next = dmi_tdo
                    elif dtmcs_selected:
                        tdo_o.next = dtmcs_tdo
                    else:
                        tdo_o.next = False
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
                instruction.next = JTAG_INSTR_IDCODE
                ir_shift.next = 0
                idcode_shift.next = 0
                bypass.next = False
                dmistat.next = DTM_DMI_STATUS_OK
            elif dmireset_pulse:
                dmistat.next = DTM_DMI_STATUS_OK

            if trstn_sync and tck_rise:
                if tap_state == t_tap_state.test_logic_reset and tms_sync:
                    instruction.next = JTAG_INSTR_IDCODE

                if tap_state == t_tap_state.capture_ir:
                    ir_shift.next = 0x01
                elif tap_state == t_tap_state.shift_ir:
                    ir_shift.next[JTAG_IR_WIDTH - 1] = tdi_sync
                    ir_shift.next[JTAG_IR_WIDTH - 1:0] = ir_shift[JTAG_IR_WIDTH:1]
                elif tap_state == t_tap_state.update_ir:
                    instruction.next = ir_shift

                if tap_state == t_tap_state.capture_dr:
                    if instruction == JTAG_INSTR_IDCODE:
                        idcode_shift.next = JTAG_IDCODE
                    elif instruction == JTAG_INSTR_BYPASS:
                        bypass.next = False
                elif tap_state == t_tap_state.shift_dr:
                    if instruction == JTAG_INSTR_BYPASS:
                        bypass.next = tdi_sync
                    elif instruction == JTAG_INSTR_IDCODE:
                        idcode_shift.next[31] = tdi_sync
                        idcode_shift.next[31:0] = idcode_shift[32:1]

        dmi_scan = DmiScanRegister(
            self.config,
            clock,
            reset,
            dmi_selected,
            dmi_capture,
            dmi_shift,
            dmi_update,
            tdi_sync,
            dmi_tdo,
            dtm,
        )

        dtmcs_scan = DtmcsScanRegister(
            self.config,
            clock,
            reset,
            dtmcs_selected,
            dtmcs_capture,
            dtmcs_shift,
            dtmcs_update,
            tdi_sync,
            dtmcs_tdo,
            dmistat,
            dmireset_pulse,
        )

        return instances()

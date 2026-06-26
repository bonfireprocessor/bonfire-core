"""
Simulation-oriented ECP5 JTAGG TAP emulator.
(c) 2026 The Bonfire Project
License: See LICENSE
"""
from __future__ import annotations

from typing import Any

from myhdl import Signal, always_comb, always_seq, block, instances, modbv

from rtl.debug.ecp5_jtagg_client import (
    ECP5_JTAGG_IR_ER1,
    ECP5_JTAGG_IR_ER2,
    ECP5_JTAGG_IR_WIDTH,
    Ecp5JtaggInputBundle,
    Ecp5JtaggOutputBundle,
)
from rtl.debug.jtag_dtm import t_tap_state
from rtl.type_aliases import BitSignal

ECP5_JTAG_INSTR_IDCODE = 0x01
ECP5_JTAG_INSTR_BYPASS = 0xFF
ECP5_JTAG_IDCODE_LFE5U_25F = 0x41111043
ECP5_JTAG_IDCODE_LFE5U_45F = 0x41112043
ECP5_JTAG_IDCODE_LFE5U_85F = 0x41113043
ECP5_JTAG_IDCODE_DEFAULT = ECP5_JTAG_IDCODE_LFE5U_25F
ECP5_JTAG_EXPECTED_IDCODES = (
    ECP5_JTAG_IDCODE_LFE5U_25F,
    ECP5_JTAG_IDCODE_LFE5U_45F,
    ECP5_JTAG_IDCODE_LFE5U_85F,
)


class Ecp5JtaggTapEmulator:
    def __init__(self, idcode: int = ECP5_JTAG_IDCODE_DEFAULT) -> None:
        self.ir_width = ECP5_JTAGG_IR_WIDTH
        self.idcode = idcode

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
        jtagg_i: Ecp5JtaggInputBundle,
        jtagg_o: Ecp5JtaggOutputBundle,
        tap_state_o: Any = None,
    ) -> Any:
        tap_state = Signal(t_tap_state.test_logic_reset)
        instruction = Signal(modbv(ECP5_JTAG_INSTR_IDCODE)[self.ir_width:])
        ir_shift = Signal(modbv(0)[self.ir_width:])
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

        @always_seq(clock.posedge, reset=reset)
        def input_sync():
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
        def edge_detect():
            tck_rise.next = tck_sync and not tck_sync_d
            tck_fall.next = not tck_sync and tck_sync_d

        @always_comb
        def jtagg_drive():
            jtagg_i.jtck.next = tck_sync
            jtagg_i.jtdi.next = tdi_sync
            jtagg_i.jshift.next = tap_state == t_tap_state.shift_dr
            jtagg_i.jupdate.next = tap_state == t_tap_state.update_dr
            jtagg_i.jrstn.next = trstn_sync and tap_state != t_tap_state.test_logic_reset
            jtagg_i.jce1.next = instruction == ECP5_JTAGG_IR_ER1 and (
                tap_state == t_tap_state.capture_dr or tap_state == t_tap_state.shift_dr
            )
            jtagg_i.jce2.next = instruction == ECP5_JTAGG_IR_ER2 and (
                tap_state == t_tap_state.capture_dr or tap_state == t_tap_state.shift_dr
            )
            jtagg_i.jrt1.next = instruction == ECP5_JTAGG_IR_ER1 and tap_state == t_tap_state.run_test_idle
            jtagg_i.jrt2.next = instruction == ECP5_JTAGG_IR_ER2 and tap_state == t_tap_state.run_test_idle

        @always_seq(clock.posedge, reset=reset)
        def tdo_select():
            if not trstn_sync:
                tdo_o.next = False
            elif tck_fall:
                if tap_state == t_tap_state.shift_ir:
                    tdo_o.next = ir_shift[0]
                elif tap_state == t_tap_state.shift_dr:
                    if instruction == ECP5_JTAG_INSTR_IDCODE:
                        tdo_o.next = idcode_shift[0]
                    elif instruction == ECP5_JTAGG_IR_ER1:
                        tdo_o.next = jtagg_o.jtdo1
                    elif instruction == ECP5_JTAGG_IR_ER2:
                        tdo_o.next = jtagg_o.jtdo2
                    else:
                        tdo_o.next = bypass
                else:
                    tdo_o.next = False

        if tap_state_o is not None:
            @always_comb
            def tap_state_observe():
                tap_state_o.next = tap_state

        @always_seq(clock.posedge, reset=reset)
        def state_transition():
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
        def actions():
            if not trstn_sync:
                instruction.next = ECP5_JTAG_INSTR_IDCODE
                ir_shift.next = 0
                idcode_shift.next = 0
                bypass.next = False
            elif tck_rise:
                if tap_state == t_tap_state.test_logic_reset and tms_sync:
                    instruction.next = ECP5_JTAG_INSTR_IDCODE

                if tap_state == t_tap_state.capture_ir:
                    ir_shift.next = 0x01
                elif tap_state == t_tap_state.shift_ir:
                    ir_shift.next[self.ir_width - 1] = tdi_sync
                    ir_shift.next[self.ir_width - 1:0] = ir_shift[self.ir_width:1]
                elif tap_state == t_tap_state.update_ir:
                    instruction.next = ir_shift

                if tap_state == t_tap_state.capture_dr:
                    if instruction == ECP5_JTAG_INSTR_IDCODE:
                        idcode_shift.next = self.idcode
                    else:
                        bypass.next = False
                elif tap_state == t_tap_state.shift_dr:
                    if instruction == ECP5_JTAG_INSTR_IDCODE:
                        idcode_shift.next[31] = tdi_sync
                        idcode_shift.next[31:0] = idcode_shift[32:1]
                    elif instruction != ECP5_JTAGG_IR_ER1 and instruction != ECP5_JTAGG_IR_ER2:
                        bypass.next = tdi_sync

        return instances()

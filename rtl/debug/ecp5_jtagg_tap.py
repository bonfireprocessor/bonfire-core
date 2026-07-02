"""
Simulation-oriented ECP5 JTAGG TAP emulator.
(c) 2026 The Bonfire Project
License: See LICENSE
"""
from __future__ import annotations

from typing import Any

from myhdl import Signal, always, always_comb, block, delay, instance, instances, modbv

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

        @always_comb
        def jtagg_drive():
            jtagg_i.jshift.next = tap_state == t_tap_state.shift_dr
            jtagg_i.jupdate.next = tap_state == t_tap_state.update_dr
            jtagg_i.jrstn.next = trstn_i and tap_state != t_tap_state.test_logic_reset
            jtagg_i.jce1.next = instruction == ECP5_JTAGG_IR_ER1 and (
                tap_state == t_tap_state.capture_dr or tap_state == t_tap_state.shift_dr
            )
            jtagg_i.jce2.next = instruction == ECP5_JTAGG_IR_ER2 and (
                tap_state == t_tap_state.capture_dr or tap_state == t_tap_state.shift_dr
            )
            jtagg_i.jrt1.next = instruction == ECP5_JTAGG_IR_ER1 and tap_state == t_tap_state.run_test_idle
            jtagg_i.jrt2.next = instruction == ECP5_JTAGG_IR_ER2 and tap_state == t_tap_state.run_test_idle

        @instance
        def jtagg_clock_and_data():
            while True:
                yield tck_i.posedge
                jtagg_i.jtck.next = True
                # Let JTCK-clocked user logic consume the previously
                # registered JTDI value before publishing the new one.
                yield delay(0)
                jtagg_i.jtdi.next = tdi_i
                yield tck_i.negedge
                jtagg_i.jtck.next = False

        @always(tck_i.negedge)
        def tdo_select():
            if reset or not trstn_i:
                tdo_o.next = False
            elif tap_state == t_tap_state.shift_ir:
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

        @always(tck_i.posedge)
        def state_transition():
            if reset or not trstn_i:
                tap_state.next = t_tap_state.test_logic_reset
            else:
                if tap_state == t_tap_state.test_logic_reset:
                    if tms_i:
                        tap_state.next = t_tap_state.test_logic_reset
                    else:
                        tap_state.next = t_tap_state.run_test_idle
                elif tap_state == t_tap_state.run_test_idle:
                    if tms_i:
                        tap_state.next = t_tap_state.select_dr_scan
                    else:
                        tap_state.next = t_tap_state.run_test_idle
                elif tap_state == t_tap_state.select_dr_scan:
                    if tms_i:
                        tap_state.next = t_tap_state.select_ir_scan
                    else:
                        tap_state.next = t_tap_state.capture_dr
                elif tap_state == t_tap_state.capture_dr:
                    if tms_i:
                        tap_state.next = t_tap_state.exit1_dr
                    else:
                        tap_state.next = t_tap_state.shift_dr
                elif tap_state == t_tap_state.shift_dr:
                    if tms_i:
                        tap_state.next = t_tap_state.exit1_dr
                    else:
                        tap_state.next = t_tap_state.shift_dr
                elif tap_state == t_tap_state.exit1_dr:
                    if tms_i:
                        tap_state.next = t_tap_state.update_dr
                    else:
                        tap_state.next = t_tap_state.pause_dr
                elif tap_state == t_tap_state.pause_dr:
                    if tms_i:
                        tap_state.next = t_tap_state.exit2_dr
                    else:
                        tap_state.next = t_tap_state.pause_dr
                elif tap_state == t_tap_state.exit2_dr:
                    if tms_i:
                        tap_state.next = t_tap_state.update_dr
                    else:
                        tap_state.next = t_tap_state.shift_dr
                elif tap_state == t_tap_state.update_dr:
                    if tms_i:
                        tap_state.next = t_tap_state.select_dr_scan
                    else:
                        tap_state.next = t_tap_state.run_test_idle
                elif tap_state == t_tap_state.select_ir_scan:
                    if tms_i:
                        tap_state.next = t_tap_state.test_logic_reset
                    else:
                        tap_state.next = t_tap_state.capture_ir
                elif tap_state == t_tap_state.capture_ir:
                    if tms_i:
                        tap_state.next = t_tap_state.exit1_ir
                    else:
                        tap_state.next = t_tap_state.shift_ir
                elif tap_state == t_tap_state.shift_ir:
                    if tms_i:
                        tap_state.next = t_tap_state.exit1_ir
                    else:
                        tap_state.next = t_tap_state.shift_ir
                elif tap_state == t_tap_state.exit1_ir:
                    if tms_i:
                        tap_state.next = t_tap_state.update_ir
                    else:
                        tap_state.next = t_tap_state.pause_ir
                elif tap_state == t_tap_state.pause_ir:
                    if tms_i:
                        tap_state.next = t_tap_state.exit2_ir
                    else:
                        tap_state.next = t_tap_state.pause_ir
                elif tap_state == t_tap_state.exit2_ir:
                    if tms_i:
                        tap_state.next = t_tap_state.update_ir
                    else:
                        tap_state.next = t_tap_state.shift_ir
                else:
                    if tms_i:
                        tap_state.next = t_tap_state.select_dr_scan
                    else:
                        tap_state.next = t_tap_state.run_test_idle

        @always(tck_i.posedge)
        def actions():
            if reset or not trstn_i:
                instruction.next = ECP5_JTAG_INSTR_IDCODE
                ir_shift.next = 0
                idcode_shift.next = 0
                bypass.next = False
            else:
                if tap_state == t_tap_state.test_logic_reset and tms_i:
                    instruction.next = ECP5_JTAG_INSTR_IDCODE

                if tap_state == t_tap_state.capture_ir:
                    ir_shift.next = 0x01
                elif tap_state == t_tap_state.shift_ir:
                    ir_shift.next[self.ir_width - 1] = tdi_i
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
                        idcode_shift.next[31] = tdi_i
                        idcode_shift.next[31:0] = idcode_shift[32:1]
                    elif instruction != ECP5_JTAGG_IR_ER1 and instruction != ECP5_JTAGG_IR_ER2:
                        bypass.next = tdi_i

        return instances()

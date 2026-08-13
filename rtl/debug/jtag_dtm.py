"""
JTAG Debug Transport Module for the Bonfire debug module.
(c) 2026 The Bonfire Project
License: See LICENSE

This implements a small RISC-V debug compatible TAP with IDCODE, DTMCS, DMI
and BYPASS instructions. TAP and scan registers run directly in the TCK domain;
complete DMI transactions cross into the core clock domain through a toggle
handshake.
"""
from __future__ import annotations

from typing import Any

from myhdl import Signal, always, always_comb, block, instances, modbv

import rtl.debug.constants as constants
from rtl.debug.dm_registers import DmiBundle
from rtl.debug.dtm_transport import (
    DmiCdcBridge,
)
from rtl.debug.tap_fsm import TapStateController, t_tap_state
from rtl.type_aliases import BitSignal


JTAG_IR_WIDTH = 5

JTAG_INSTR_IDCODE = 0x01
JTAG_INSTR_DTMCS = 0x10
JTAG_INSTR_DMI = 0x11
JTAG_INSTR_BYPASS = 0x1F

JTAG_IDCODE = 0x10E31913

DTM_DMI_STATUS_OK = 0


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
        abits = self.config.dmi_adr_width
        dmi_width = abits + 34

        tap_state = Signal(t_tap_state.test_logic_reset)
        instruction = Signal(modbv(JTAG_INSTR_IDCODE)[JTAG_IR_WIDTH:])
        ir_shift = Signal(modbv(0)[JTAG_IR_WIDTH:])
        idcode_shift = Signal(modbv(0)[32:])
        bypass = Signal(bool(0))
        dmi_shift_reg = Signal(modbv(0)[dmi_width:])
        dtmcs_shift_reg = Signal(modbv(0)[32:])

        request_payload = Signal(modbv(0)[dmi_width:])
        request_toggle = Signal(bool(0))
        dmireset_toggle = Signal(bool(0))
        response_payload = Signal(modbv(0)[dmi_width:])
        request_pending = Signal(bool(0))

        if tap_state_o is not None:
            @always_comb
            def tap_state_observe():
                tap_state_o.next = tap_state

        @always(tck_i.negedge)
        def tdo_select():
            if reset or not trstn_i:
                tdo_o.next = False
            elif tap_state == t_tap_state.shift_ir:
                tdo_o.next = ir_shift[0]
            elif tap_state == t_tap_state.shift_dr:
                if instruction == JTAG_INSTR_BYPASS:
                    tdo_o.next = bypass
                elif instruction == JTAG_INSTR_IDCODE:
                    tdo_o.next = idcode_shift[0]
                elif instruction == JTAG_INSTR_DMI:
                    tdo_o.next = dmi_shift_reg[0]
                elif instruction == JTAG_INSTR_DTMCS:
                    tdo_o.next = dtmcs_shift_reg[0]
                else:
                    tdo_o.next = False
            else:
                tdo_o.next = False

        @always(tck_i.posedge)
        def tap_actions():
            if reset or not trstn_i:
                instruction.next = JTAG_INSTR_IDCODE
                ir_shift.next = 0
                idcode_shift.next = 0
                bypass.next = False
                dmi_shift_reg.next = 0
                dtmcs_shift_reg.next = 0
                request_payload.next = 0
                request_toggle.next = False
                dmireset_toggle.next = False
            else:
                if tap_state == t_tap_state.test_logic_reset and tms_i:
                    instruction.next = JTAG_INSTR_IDCODE

                if tap_state == t_tap_state.capture_ir:
                    ir_shift.next = 0x01
                elif tap_state == t_tap_state.shift_ir:
                    ir_shift.next[JTAG_IR_WIDTH - 1] = tdi_i
                    ir_shift.next[JTAG_IR_WIDTH - 1:0] = ir_shift[JTAG_IR_WIDTH:1]
                elif tap_state == t_tap_state.update_ir:
                    instruction.next = ir_shift

                if tap_state == t_tap_state.capture_dr:
                    if instruction == JTAG_INSTR_IDCODE:
                        idcode_shift.next = JTAG_IDCODE
                    elif instruction == JTAG_INSTR_BYPASS:
                        bypass.next = False
                    elif instruction == JTAG_INSTR_DMI:
                        if request_pending:
                            busy_response = modbv(0)[dmi_width:]
                            busy_response[2:0] = constants.DMI_OP_BUSY
                            dmi_shift_reg.next = busy_response
                        else:
                            dmi_shift_reg.next = response_payload
                    elif instruction == JTAG_INSTR_DTMCS:
                        dtmcs = modbv(0)[32:]
                        dtmcs[3:0] = constants.DTM_VERSION
                        dtmcs[9:4] = abits
                        if request_pending:
                            dtmcs[12:10] = constants.DMI_OP_BUSY
                        dtmcs[15:12] = constants.DTM_IDLE
                        dtmcs_shift_reg.next = dtmcs
                elif tap_state == t_tap_state.shift_dr:
                    if instruction == JTAG_INSTR_BYPASS:
                        bypass.next = tdi_i
                    elif instruction == JTAG_INSTR_IDCODE:
                        idcode_shift.next[31] = tdi_i
                        idcode_shift.next[31:0] = idcode_shift[32:1]
                    elif instruction == JTAG_INSTR_DMI:
                        dmi_shift_reg.next[dmi_width - 1] = tdi_i
                        dmi_shift_reg.next[dmi_width - 1:0] = dmi_shift_reg[dmi_width:1]
                    elif instruction == JTAG_INSTR_DTMCS:
                        dtmcs_shift_reg.next[31] = tdi_i
                        dtmcs_shift_reg.next[31:0] = dtmcs_shift_reg[32:1]
                elif tap_state == t_tap_state.update_dr:
                    if instruction == JTAG_INSTR_DMI:
                        request_payload.next = dmi_shift_reg
                        request_toggle.next = not request_toggle
                    elif instruction == JTAG_INSTR_DTMCS and dtmcs_shift_reg[16]:
                        dmireset_toggle.next = not dmireset_toggle

        tap_fsm = TapStateController(tck_i, reset, trstn_i, tms_i, tap_state)
        dmi_cdc = DmiCdcBridge(
            self.config,
            clock,
            reset,
            tck_i,
            trstn_i,
            request_payload,
            request_toggle,
            dmireset_toggle,
            response_payload,
            request_pending,
            dtm,
        )

        return instances()

"""
ECP5 JTAGG-based debug transport frontend.
(c) 2026 The Bonfire Project
License: See LICENSE
"""
from __future__ import annotations

from typing import Any

from myhdl import Signal, always, always_comb, block, instances, modbv

from rtl.debug.dm_registers import DmiBundle
from rtl.debug.dtm_transport import (
    DMI_OP_BUSY,
    DmiCdcBridge,
    DTM_IDLE,
    DTM_VERSION,
    DTMCS_DMIRESET_BIT,
)
from rtl.type_aliases import BitSignal

ECP5_JTAGG_IR_ER1 = 0x32
ECP5_JTAGG_IR_ER2 = 0x38
ECP5_JTAGG_IR_WIDTH = 8

class Ecp5JtaggInputBundle:
    def __init__(self) -> None:
        self.jtck = Signal(bool(0))
        self.jtdi = Signal(bool(0))
        self.jshift = Signal(bool(0))
        self.jupdate = Signal(bool(0))
        self.jrstn = Signal(bool(1))
        self.jce1 = Signal(bool(0))
        self.jce2 = Signal(bool(0))
        self.jrt1 = Signal(bool(0))
        self.jrt2 = Signal(bool(0))


class Ecp5JtaggOutputBundle:
    def __init__(self) -> None:
        self.jtdo1 = Signal(bool(0))
        self.jtdo2 = Signal(bool(0))


@block
def Ecp5JtaggClient(
    config: Any,
    clock: BitSignal,
    reset: BitSignal,
    jtagg_i: Ecp5JtaggInputBundle,
    jtagg_o: Ecp5JtaggOutputBundle,
    dtm: DmiBundle,
) -> Any:
    abits = config.dmi_adr_width
    dmi_width = abits + 34

    dmi_shift_reg = Signal(modbv(0)[dmi_width:])
    dtmcs_shift_reg = Signal(modbv(0)[32:])
    active_er1 = Signal(bool(0))
    active_er2 = Signal(bool(0))
    jshift_d = Signal(bool(0))

    request_payload = Signal(modbv(0)[dmi_width:])
    request_toggle = Signal(bool(0))
    dmireset_toggle = Signal(bool(0))

    response_payload = Signal(modbv(0)[dmi_width:])
    request_pending = Signal(bool(0))

    @always_comb
    def outputs():
        jtagg_o.jtdo1.next = dmi_shift_reg[0]
        jtagg_o.jtdo2.next = dtmcs_shift_reg[0]

    @always(jtagg_i.jtck.posedge)
    def jtag_clock_domain():
        if reset or not jtagg_i.jrstn:
            dmi_shift_reg.next = 0
            dtmcs_shift_reg.next = 0
            active_er1.next = False
            active_er2.next = False
            jshift_d.next = False
            request_payload.next = 0
            request_toggle.next = False
            dmireset_toggle.next = False
        else:
            jshift_d.next = jtagg_i.jshift

            if jtagg_i.jce1 and not jtagg_i.jshift:
                active_er1.next = True
                active_er2.next = False
                if request_pending:
                    busy_response = modbv(0)[dmi_width:]
                    busy_response[2:0] = DMI_OP_BUSY
                    dmi_shift_reg.next = busy_response
                else:
                    dmi_shift_reg.next = response_payload
            elif jtagg_i.jce2 and not jtagg_i.jshift:
                active_er1.next = False
                active_er2.next = True
                dtmcs = modbv(0)[32:]
                dtmcs[3:0] = DTM_VERSION
                dtmcs[9:4] = abits
                if request_pending:
                    dtmcs[12:10] = DMI_OP_BUSY
                dtmcs[15:12] = DTM_IDLE
                dtmcs_shift_reg.next = dtmcs
            elif jtagg_i.jshift:
                # JTAGG registers JTDI on this edge. Ignore it on the first
                # shift edge, but advance TDO to the next LSB. From the next
                # edge onward JTDI is the previous bit.
                if jshift_d:
                    if active_er1:
                        dmi_shift_reg.next[dmi_width - 1] = jtagg_i.jtdi
                        dmi_shift_reg.next[dmi_width - 1:0] = dmi_shift_reg[dmi_width:1]
                    elif active_er2:
                        dtmcs_shift_reg.next[31] = jtagg_i.jtdi
                        dtmcs_shift_reg.next[31:0] = dtmcs_shift_reg[32:1]
                elif active_er1:
                    dmi_shift_reg.next = dmi_shift_reg >> 1
                elif active_er2:
                    dtmcs_shift_reg.next = dtmcs_shift_reg >> 1
            elif jshift_d:
                # The final registered JTDI bit becomes visible after JSHIFT
                # falls, before the following Update-DR clock.
                if active_er1:
                    dmi_shift_reg.next[dmi_width - 1] = jtagg_i.jtdi
                    dmi_shift_reg.next[dmi_width - 1:0] = dmi_shift_reg[dmi_width:1]
                elif active_er2:
                    dtmcs_shift_reg.next[31] = jtagg_i.jtdi
                    dtmcs_shift_reg.next[31:0] = dtmcs_shift_reg[32:1]
            elif jtagg_i.jupdate:
                if active_er1:
                    request_payload.next = dmi_shift_reg
                    request_toggle.next = not request_toggle
                elif active_er2 and dtmcs_shift_reg[DTMCS_DMIRESET_BIT]:
                    dmireset_toggle.next = not dmireset_toggle
            elif jtagg_i.jrt1:
                active_er1.next = True
                active_er2.next = False
            elif jtagg_i.jrt2:
                active_er1.next = False
                active_er2.next = True

    dmi_cdc = DmiCdcBridge(
        config,
        clock,
        reset,
        jtagg_i.jtck,
        jtagg_i.jrstn,
        request_payload,
        request_toggle,
        dmireset_toggle,
        response_payload,
        request_pending,
        dtm,
    )

    return instances()

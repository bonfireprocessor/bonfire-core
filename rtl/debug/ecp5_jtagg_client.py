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
    DMI_OP_READ,
    DMI_OP_SUCCESS,
    DMI_OP_WRITE,
    DTM_IDLE,
    DTM_VERSION,
    DTMCS_DMIRESET_BIT,
)
from rtl.type_aliases import BitSignal

ECP5_JTAGG_IR_ER1 = 0x32
ECP5_JTAGG_IR_ER2 = 0x38
ECP5_JTAGG_IR_WIDTH = 8

DMI_OP_BUSY = 3


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
    response_toggle = Signal(bool(0))
    response_toggle_meta = Signal(bool(0))
    response_toggle_sync = Signal(bool(0))

    request_toggle_meta = Signal(bool(0))
    request_toggle_sync = Signal(bool(0))
    request_toggle_seen = Signal(bool(0))
    dmireset_toggle_meta = Signal(bool(0))
    dmireset_toggle_sync = Signal(bool(0))
    dmireset_toggle_seen = Signal(bool(0))

    request_active = Signal(bool(0))
    read_pending = Signal(bool(0))
    read_capture = Signal(bool(0))

    @always_comb
    def outputs():
        jtagg_o.jtdo1.next = dmi_shift_reg[0]
        jtagg_o.jtdo2.next = dtmcs_shift_reg[0]

    @always(jtagg_i.jtck.posedge)
    def jtag_clock_domain():
        response_toggle_meta.next = response_toggle
        response_toggle_sync.next = response_toggle_meta

        if reset or not jtagg_i.jrstn:
            dmi_shift_reg.next = 0
            dtmcs_shift_reg.next = 0
            active_er1.next = False
            active_er2.next = False
            jshift_d.next = False
            request_payload.next = 0
            request_toggle.next = False
            dmireset_toggle.next = False
            response_toggle_meta.next = False
            response_toggle_sync.next = False
        else:
            jshift_d.next = jtagg_i.jshift

            if jtagg_i.jce1 and not jtagg_i.jshift:
                active_er1.next = True
                active_er2.next = False
                if request_toggle != response_toggle_sync:
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
                if request_toggle != response_toggle_sync:
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

    @always(clock.posedge)
    def core_clock_domain():
        request_toggle_meta.next = request_toggle
        request_toggle_sync.next = request_toggle_meta
        dmireset_toggle_meta.next = dmireset_toggle
        dmireset_toggle_sync.next = dmireset_toggle_meta

        if reset:
            request_toggle_meta.next = False
            request_toggle_sync.next = False
            request_toggle_seen.next = False
            dmireset_toggle_meta.next = False
            dmireset_toggle_sync.next = False
            dmireset_toggle_seen.next = False
            request_active.next = False
            read_pending.next = False
            read_capture.next = False
            response_payload.next = 0
            response_toggle.next = False
            dtm.en.next = False
            dtm.we.next = False
            dtm.adr.next = 0
            dtm.dbi.next = 0
        else:
            if dmireset_toggle_sync != dmireset_toggle_seen:
                dmireset_toggle_seen.next = dmireset_toggle_sync
                request_toggle_seen.next = request_toggle_sync
                request_active.next = False
                read_pending.next = False
                read_capture.next = False
                response_payload.next = 0
                response_toggle.next = request_toggle_sync
                dtm.en.next = False
                dtm.we.next = False
            elif request_active:
                dtm.en.next = False
                dtm.we.next = False
                request_active.next = False
                if read_pending:
                    read_pending.next = False
                    read_capture.next = True
                else:
                    response_toggle.next = request_toggle_seen
            elif read_capture:
                response_payload.next[2:0] = DMI_OP_SUCCESS
                response_payload.next[34:2] = dtm.dbo
                response_toggle.next = request_toggle_seen
                read_capture.next = False
            elif request_toggle_sync != request_toggle_seen:
                request_toggle_seen.next = request_toggle_sync
                dtm.adr.next = request_payload[dmi_width:34]
                dtm.dbi.next = request_payload[34:2]
                response_payload.next[2:0] = DMI_OP_SUCCESS
                response_payload.next[34:2] = 0
                response_payload.next[dmi_width:34] = request_payload[dmi_width:34]

                if request_payload[2:0] == DMI_OP_READ:
                    dtm.we.next = False
                    dtm.en.next = True
                    request_active.next = True
                    read_pending.next = True
                elif request_payload[2:0] == DMI_OP_WRITE:
                    dtm.we.next = True
                    dtm.en.next = True
                    request_active.next = True
                else:
                    dtm.en.next = False
                    dtm.we.next = False
                    response_toggle.next = request_toggle_sync

    return instances()

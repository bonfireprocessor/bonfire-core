"""
ECP5 JTAGG-based debug transport frontend.
(c) 2026 The Bonfire Project
License: See LICENSE
"""
from __future__ import annotations

from typing import Any

from myhdl import Signal, always_comb, always_seq, block, instances, intbv

from rtl.debug.dm_registers import DmiBundle
from rtl.debug.dtm_transport import DmiScanRegister, DtmcsScanRegister
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
    jtck_meta = Signal(bool(0))
    jtck_sync = Signal(bool(0))
    jtck_sync_d = Signal(bool(0))
    jtdi_meta = Signal(bool(0))
    jtdi_sync = Signal(bool(0))
    jshift_meta = Signal(bool(0))
    jshift_sync = Signal(bool(0))
    jupdate_meta = Signal(bool(0))
    jupdate_sync = Signal(bool(0))
    jrstn_meta = Signal(bool(1))
    jrstn_sync = Signal(bool(1))
    jce1_meta = Signal(bool(0))
    jce1_sync = Signal(bool(0))
    jce2_meta = Signal(bool(0))
    jce2_sync = Signal(bool(0))
    jrt1_meta = Signal(bool(0))
    jrt1_sync = Signal(bool(0))
    jrt2_meta = Signal(bool(0))
    jrt2_sync = Signal(bool(0))

    jtck_rise = Signal(bool(0))

    dmi_capture = Signal(bool(0))
    dmi_shift = Signal(bool(0))
    dmi_update = Signal(bool(0))
    dtmcs_capture = Signal(bool(0))
    dtmcs_shift = Signal(bool(0))
    dtmcs_update = Signal(bool(0))

    dmi_tdo = Signal(bool(0))
    dtmcs_tdo = Signal(bool(0))
    dmistat = Signal(intbv(0)[2:])
    dmireset_pulse = Signal(bool(0))
    active_er1 = Signal(bool(0))
    active_er2 = Signal(bool(0))
    always_active = Signal(bool(1))

    @always_seq(clock.posedge, reset=reset)
    def sync_inputs():
        jtck_meta.next = jtagg_i.jtck
        jtck_sync.next = jtck_meta
        jtck_sync_d.next = jtck_sync
        jtdi_meta.next = jtagg_i.jtdi
        jtdi_sync.next = jtdi_meta
        jshift_meta.next = jtagg_i.jshift
        jshift_sync.next = jshift_meta
        jupdate_meta.next = jtagg_i.jupdate
        jupdate_sync.next = jupdate_meta
        jrstn_meta.next = jtagg_i.jrstn
        jrstn_sync.next = jrstn_meta
        jce1_meta.next = jtagg_i.jce1
        jce1_sync.next = jce1_meta
        jce2_meta.next = jtagg_i.jce2
        jce2_sync.next = jce2_meta
        jrt1_meta.next = jtagg_i.jrt1
        jrt1_sync.next = jrt1_meta
        jrt2_meta.next = jtagg_i.jrt2
        jrt2_sync.next = jrt2_meta

    @always_comb
    def edge_detect():
        jtck_rise.next = jtck_sync and not jtck_sync_d

    @always_seq(clock.posedge, reset=reset)
    def derive_controls():
        dmi_capture.next = False
        dmi_shift.next = False
        dmi_update.next = False
        dtmcs_capture.next = False
        dtmcs_shift.next = False
        dtmcs_update.next = False

        if not jrstn_sync:
            active_er1.next = False
            active_er2.next = False
        elif jtck_rise:
            if jce1_sync:
                active_er1.next = True
                active_er2.next = False
                if jshift_sync:
                    dmi_shift.next = True
                else:
                    dmi_capture.next = True
            elif jce2_sync:
                active_er1.next = False
                active_er2.next = True
                if jshift_sync:
                    dtmcs_shift.next = True
                else:
                    dtmcs_capture.next = True
            elif jupdate_sync:
                if active_er1:
                    dmi_update.next = True
                elif active_er2:
                    dtmcs_update.next = True
            elif jrt1_sync:
                active_er1.next = True
                active_er2.next = False
            elif jrt2_sync:
                active_er1.next = False
                active_er2.next = True

    @always_comb
    def outputs():
        jtagg_o.jtdo1.next = dmi_tdo
        jtagg_o.jtdo2.next = dtmcs_tdo

    dmi_scan = DmiScanRegister(
        config,
        clock,
        reset,
        always_active,
        dmi_capture,
        dmi_shift,
        dmi_update,
        jtdi_sync,
        dmi_tdo,
        dtm,
    )

    dtmcs_scan = DtmcsScanRegister(
        config,
        clock,
        reset,
        always_active,
        dtmcs_capture,
        dtmcs_shift,
        dtmcs_update,
        jtdi_sync,
        dtmcs_tdo,
        dmistat,
        dmireset_pulse,
    )

    return instances()

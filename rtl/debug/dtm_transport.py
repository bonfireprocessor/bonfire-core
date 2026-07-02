"""
Shared clock-domain crossing for RISC-V debug transport frontends.
(c) 2026 The Bonfire Project
License: See LICENSE
"""
from __future__ import annotations

from typing import Any

from myhdl import Signal, always, always_comb, block, instances, modbv

from rtl.debug.dm_registers import DmiBundle
from rtl.type_aliases import BitSignal

DMI_OP_READ = 1
DMI_OP_WRITE = 2
DMI_OP_SUCCESS = 0
DMI_OP_BUSY = 3
DTM_VERSION = 1
DTM_IDLE = 1
DTMCS_DMIRESET_BIT = 16


@block
def DmiCdcBridge(
    config: Any,
    core_clock: BitSignal,
    reset: BitSignal,
    scan_clock: BitSignal,
    scan_resetn: BitSignal,
    request_payload_i: Any,
    request_toggle_i: BitSignal,
    dmireset_toggle_i: BitSignal,
    response_payload_o: Any,
    pending_o: BitSignal,
    dtm: DmiBundle,
) -> Any:
    """Transfer complete DMI transactions between scan and core clocks."""

    abits = config.dmi_adr_width
    dmi_width = abits + 34

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
    def pending():
        pending_o.next = request_toggle_i != response_toggle_sync

    @always(scan_clock.posedge)
    def response_sync():
        if reset or not scan_resetn:
            response_toggle_meta.next = False
            response_toggle_sync.next = False
        else:
            response_toggle_meta.next = response_toggle
            response_toggle_sync.next = response_toggle_meta

    @always(core_clock.posedge)
    def core_clock_domain():
        request_toggle_meta.next = request_toggle_i
        request_toggle_sync.next = request_toggle_meta
        dmireset_toggle_meta.next = dmireset_toggle_i
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
            response_payload_o.next = 0
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
                response_payload_o.next = 0
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
                response_payload_o.next[2:0] = DMI_OP_SUCCESS
                response_payload_o.next[34:2] = dtm.dbo
                response_toggle.next = request_toggle_seen
                read_capture.next = False
            elif request_toggle_sync != request_toggle_seen:
                request_toggle_seen.next = request_toggle_sync
                dtm.adr.next = request_payload_i[dmi_width:34]
                dtm.dbi.next = request_payload_i[34:2]
                response_payload_o.next[2:0] = DMI_OP_SUCCESS
                response_payload_o.next[34:2] = 0
                response_payload_o.next[dmi_width:34] = request_payload_i[dmi_width:34]

                if request_payload_i[2:0] == DMI_OP_READ:
                    dtm.we.next = False
                    dtm.en.next = True
                    request_active.next = True
                    read_pending.next = True
                elif request_payload_i[2:0] == DMI_OP_WRITE:
                    dtm.we.next = True
                    dtm.en.next = True
                    request_active.next = True
                else:
                    dtm.en.next = False
                    dtm.we.next = False
                    response_toggle.next = request_toggle_sync

    return instances()

"""
Shared scan-register transport blocks for RISC-V debug DTM frontends.
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
DTM_VERSION = 1
DTM_IDLE = 1
DTMCS_DMIRESET_BIT = 16


@block
def DmiScanRegister(
    config: Any,
    clock: BitSignal,
    reset: BitSignal,
    active_i: BitSignal,
    capture_i: BitSignal,
    shift_i: BitSignal,
    update_i: BitSignal,
    tdi_i: BitSignal,
    tdo_o: BitSignal,
    dtm: DmiBundle,
) -> Any:
    abits = config.dmi_adr_width
    width = abits + 34

    shift_reg = Signal(modbv(0)[width:])
    response_reg = Signal(modbv(0)[width:])
    request_active = Signal(bool(0))
    read_pending = Signal(bool(0))
    read_capture = Signal(bool(0))

    @always_comb
    def comb():
        tdo_o.next = shift_reg[0]

    @always(clock.posedge)
    def seq():
        if reset:
            shift_reg.next = 0
            response_reg.next = 0
            request_active.next = False
            read_pending.next = False
            read_capture.next = False
            dtm.en.next = False
            dtm.we.next = False
            dtm.adr.next = 0
            dtm.dbi.next = 0
        else:
            if request_active:
                dtm.en.next = False
                dtm.we.next = False
                request_active.next = False
                if read_pending:
                    read_pending.next = False
                    read_capture.next = True

            elif read_capture:
                response_reg.next[2:0] = DMI_OP_SUCCESS
                response_reg.next[34:2] = dtm.dbo
                read_capture.next = False

            if capture_i and active_i:
                shift_reg.next = response_reg
            elif shift_i and active_i:
                shift_reg.next[width - 1] = tdi_i
                shift_reg.next[width - 1:0] = shift_reg[width:1]
            elif update_i and active_i:
                op = shift_reg[2:0]
                dtm.adr.next = shift_reg[width:34]
                dtm.dbi.next = shift_reg[34:2]

                if op == DMI_OP_READ:
                    dtm.we.next = False
                    dtm.en.next = True
                    request_active.next = True
                    read_pending.next = True
                    response_reg.next[2:0] = DMI_OP_SUCCESS
                    response_reg.next[34:2] = 0
                    response_reg.next[width:34] = shift_reg[width:34]
                elif op == DMI_OP_WRITE:
                    dtm.we.next = True
                    dtm.en.next = True
                    request_active.next = True
                    response_reg.next[2:0] = DMI_OP_SUCCESS
                    response_reg.next[34:2] = 0
                    response_reg.next[width:34] = shift_reg[width:34]
                else:
                    response_reg.next[2:0] = DMI_OP_SUCCESS
                    response_reg.next[34:2] = 0
                    response_reg.next[width:34] = shift_reg[width:34]

    return instances()


@block
def DtmcsScanRegister(
    config: Any,
    clock: BitSignal,
    reset: BitSignal,
    active_i: BitSignal,
    capture_i: BitSignal,
    shift_i: BitSignal,
    update_i: BitSignal,
    tdi_i: BitSignal,
    tdo_o: BitSignal,
    dmistat_i: Any,
    dmireset_pulse_o: BitSignal,
) -> Any:
    abits = config.dmi_adr_width
    shift_reg = Signal(modbv(0)[32:])

    @always_comb
    def comb():
        tdo_o.next = shift_reg[0]

    @always(clock.posedge)
    def seq():
        dmireset_pulse_o.next = False

        if reset:
            shift_reg.next = 0
        else:
            if capture_i and active_i:
                dtmcs = modbv(0)[32:]
                dtmcs[3:0] = DTM_VERSION
                dtmcs[9:4] = abits
                dtmcs[12:10] = dmistat_i
                dtmcs[15:12] = DTM_IDLE
                shift_reg.next = dtmcs
            elif shift_i and active_i:
                shift_reg.next[31] = tdi_i
                shift_reg.next[31:0] = shift_reg[32:1]
            elif update_i and active_i:
                if shift_reg[DTMCS_DMIRESET_BIT]:
                    dmireset_pulse_o.next = True

    return instances()

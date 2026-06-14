"""
RISC-V debug module — register bundles
(c) 2023 The Bonfire Project
License: See LICENSE
"""
from __future__ import annotations

from typing import Any

from myhdl import Signal, modbv

from rtl.debug.types import (
    t_debug_hart_state,
    t_abstract_command_type,
    t_abstract_command_state,
)
from util.diagnostics import get_diagnostics


class DebugModuleRegisterBundle:
    def __init__(self, config: Any) -> None:
        self.config = config
        xlen = config.xlen
        self.xlen = xlen

        assert self.config.progbuf_size in range(1, 3), "progbuf_size must be 1 or 2"
        get_diagnostics().detail("DebugModuleRegisterBundle: xlen={} ip_low={} numdata={} progbuf_size={} dmi_adr_width={}".format(
            config.xlen,
            config.ip_low,
            config.numdata,
            config.progbuf_size,
            config.dmi_adr_width,
        ))

        self.hart_state = Signal(t_debug_hart_state.running)

        # Signals from DMI to debug core, written by DMI
        self.haltreq = Signal(bool(0))
        self.resumereq = Signal(bool(0))
        self.hart_reset = Signal(bool(0))
        self.abstract_command_new = Signal(bool(0))

        # Abstract Command access register fields written by DMI
        self.command_type = Signal(t_abstract_command_type.access_reg)
        self.aarsize = Signal(modbv(0)[3:])
        self.aarpostincrement = Signal(bool(0))
        self.postexec = Signal(bool(0))
        self.transfer = Signal(bool(0))
        self.write = Signal(bool(0))
        self.regno = Signal(modbv(0)[5:])
        self.cmderr = Signal(modbv(0)[3:])

        # written by DMI
        self.data_regs = [Signal(modbv(0)[xlen:]) for ii in range(0, config.numdata)]
        self.progbuf0 = Signal(modbv(0)[xlen:])
        self.progbuf1 = Signal(modbv(0)[xlen:])  # will not be used when progbuf_size==1
        # abstractauto controls whether accesses to dataN/progbufN also launch
        # the currently configured abstract command. OpenOCD uses this for
        # repeated memory reads through data0 without rewriting command.
        self.abstract_auto_data = Signal(modbv(0)[config.numdata:])
        self.abstract_auto_progbuf = Signal(modbv(0)[config.progbuf_size:])

        # Abstract Command execution state, written by debug core
        self.abstract_command_state = Signal(t_abstract_command_state.none)
        self.abstract_command_result = Signal(modbv(0)[xlen:])

        # Ack Signal for halt or resume request, written by debug core
        self.req_ack = Signal(bool(0))

        # resumeack bit, used for dmstatus all/any resumeack
        self.resumeack = Signal(bool(0))

        # Internal core-to-debug signal. It marks that the currently accepted
        # pipeline instruction reached the execute result/commit point.
        self.instr_retired = Signal(bool(0))
        self.instr_retire_dpc = Signal(modbv(0)[self.config.xlen:self.config.ip_low])

        assert config.numdata <= 16, "maximum allowed debug Data Registers are 16"

        # dpc, written by debug core
        self.dpc = Signal(modbv(0)[self.config.xlen:self.config.ip_low])

        # helpers
        self.dpc_jump = Signal(bool(0))


class DmiBundle:
    def __init__(self, config: Any) -> None:
        self.config = config
        xlen = config.xlen
        self.xlen = xlen

        self.adr = Signal(modbv(0)[config.dmi_adr_width:])  # DMI address register
        self.en = Signal(bool(0))
        self.we = Signal(bool(0))
        self.dbi = Signal(modbv(0)[32:])
        self.dbo = Signal(modbv(0)[32:])

"""
RISC-V debug module — debug CSR bundles and logic
(c) 2023 The Bonfire Project
License: See LICENSE
"""
from __future__ import annotations

from typing import Any

from myhdl import Signal, modbv, block, always, always_comb, instances

from rtl.debug.dm_registers import DebugModuleRegisterBundle
from rtl.instructions import CSRAdr
from rtl.debug.types import XDEBUGVER
from rtl.type_aliases import BitSignal


class DebugCSRUpdateBundle:
    def __init__(self, config: Any) -> None:
        self.config = config
        self.xlen = config.xlen
        xlen = config.xlen

        self.dpc = Signal(modbv(0)[xlen:config.ip_low])
        self.cause = Signal(modbv(0)[3:0])
        self.we_dpc = Signal(bool(0))
        self.we_cause = Signal(bool(0))


class DebugCSRBundle:
    def __init__(self, config: Any) -> None:
        self.config = config
        self.xlen = config.xlen

        # used dcsr bits
        self.ebreakm = Signal(bool(0))   # dcsr[15]
        self.cause = Signal(modbv(0)[3:0])  # dcsr[8..6]
        self.step = Signal(bool(0))      # dcsr[2] single step mode

    @block
    def csr_write(
        self,
        we: Any,
        adr: Any,
        data: Any,
        update: DebugCSRUpdateBundle,
        debugRegs: DebugModuleRegisterBundle,
        clock: BitSignal,
        reset: BitSignal,
    ) -> Any:
        """
        we: bool Write Enable
        adr : [8:] CSR Adr
        data: [32:] Input data to write
        update: DebugCSRUpdateBundle
        debugRegs: DebugModuleRegisterBundle
        clock: clock signal
        reset : reset signal
        """

        upper = self.config.xlen
        lower = self.config.ip_low
        reset_dpc = self.config.reset_address >> lower

        @always(clock.posedge)
        def seq():
            if reset:
                self.ebreakm.next = False
                self.cause.next = 0
                self.step.next = False
                debugRegs.dpc.next = reset_dpc

            elif we:
                if adr == CSRAdr.dcsr:
                    self.ebreakm.next = data[15]
                    self.step.next = data[2]
                elif adr == CSRAdr.dpc:
                    debugRegs.dpc.next = data[upper:lower]
            else:
                if update.we_cause:
                    self.cause.next = update.cause
                if update.we_dpc:
                    debugRegs.dpc.next = update.dpc

        return instances()


class DebugCSRReadViewBundle:
    def __init__(self, config: Any) -> None:
        self.config = config
        self.xlen = config.xlen
        xlen = config.xlen

        self.valid = Signal(bool(0))
        self.data = Signal(modbv(0)[xlen:])

    @block
    def csr_read(
        self,
        reg: Any,
        debugCSRs: DebugCSRBundle,
        debugRegs: DebugModuleRegisterBundle,
    ) -> Any:

        upper = self.config.xlen
        lower = self.config.ip_low

        @always_comb
        def comb():
            self.valid.next = True
            self.data.next = 0

            if reg == CSRAdr.dcsr:
                self.data.next[32:28] = XDEBUGVER
                self.data.next[15] = debugCSRs.ebreakm
                self.data.next[9:6] = debugCSRs.cause
                self.data.next[2] = debugCSRs.step
                self.data.next[2:0] = 3
            elif reg == CSRAdr.dpc:
                self.data.next[upper:lower] = debugRegs.dpc
            else:
                self.valid.next = False

        return instances()

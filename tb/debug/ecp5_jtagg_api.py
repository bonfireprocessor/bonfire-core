"""
ECP5 JTAGG debug API.
(c) 2023-2026 The Bonfire Project
License: See LICENSE
"""
from __future__ import annotations

from collections.abc import Generator
from typing import Any

from myhdl import delay

from rtl.config import BonfireConfig
from rtl.debug.ecp5_jtagg_client import ECP5_JTAGG_IR_ER1, ECP5_JTAGG_IR_ER2, ECP5_JTAGG_IR_WIDTH
from rtl.debug.jtag_dtm import JTAG_INSTR_IDCODE
from rtl.type_aliases import BitSignal
from tb.debug.jtag_api import JtagDebugAPI


class Ecp5JtaggDebugAPI(JtagDebugAPI):
    def __init__(
        self,
        config: BonfireConfig,
        clock: BitSignal,
        tck: BitSignal,
        tms: BitSignal,
        tdi: BitSignal,
        tdo: BitSignal,
        verbose: bool = False,
    ) -> None:
        JtagDebugAPI.__init__(
            self,
            config,
            clock,
            tck,
            tms,
            tdi,
            tdo,
            verbose=verbose,
            ir_width=ECP5_JTAGG_IR_WIDTH,
            ir_idcode=JTAG_INSTR_IDCODE,
            ir_dtmcs=ECP5_JTAGG_IR_ER2,
            ir_dmi=ECP5_JTAGG_IR_ER1,
        )
        self.settle_sysclk_cycles = 6
        self.tck_low_aligned = True

    def align_tck_low(self) -> Generator[Any, None, None]:
        if False:
            yield None

    def jtag_cycle(self, tms: int, tdi: int = 0) -> Generator[Any, None, None]:
        self.tms.next = bool(tms)
        self.tdi.next = bool(tdi)
        yield delay(20)
        self.last_tdo = int(self.tdo)
        self.tck.next = True
        yield delay(50)
        self.tck.next = False
        yield delay(50)
        yield self.wait_sysclk(self.settle_sysclk_cycles)

    def reset_tap(self) -> Generator[Any, None, None]:
        yield from JtagDebugAPI.reset_tap(self)
        yield self.wait_sysclk(12)
        yield self.idle(2)

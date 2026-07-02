"""
Direct DMI debug API.
(c) 2023-2026 The Bonfire Project
License: See LICENSE
"""
from __future__ import annotations

from collections.abc import Generator
from typing import Any

from rtl.config import BonfireConfig
from tb.debug.debug_api import DebugAPI


class DmiDebugAPI(DebugAPI):
    def __init__(self, dtm_bundle: Any, clock: Any, config: BonfireConfig | None = None) -> None:
        self.dtm_bundle = dtm_bundle
        self.clock = clock
        DebugAPI.__init__(self, config=config)

    def yield_clock(self) -> Generator[Any, None, None]:
        yield self.clock.posedge

    def dmi_read(self, adr: int) -> Generator[Any, None, None]:
        yield self.clock.posedge
        self.dtm_bundle.adr.next = adr
        self.dtm_bundle.we.next = False
        self.dtm_bundle.en.next = True
        yield self.clock.posedge
        yield self.clock.posedge
        self.result._val = self.dtm_bundle.dbo
        self.dtm_bundle.en.next = False

    def dmi_write(self, adr: int, data: int) -> Generator[Any, None, None]:
        yield self.clock.posedge
        self.dtm_bundle.adr.next = adr
        self.dtm_bundle.we.next = True
        self.dtm_bundle.en.next = True
        self.dtm_bundle.dbi.next = data
        yield self.clock.posedge
        self.dtm_bundle.en.next = False

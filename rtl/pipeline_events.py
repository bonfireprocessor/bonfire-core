"""
Internal Pipeline Boundary Event Contracts
(c) 2026 The Bonfire Project
License: See LICENSE
"""

from __future__ import annotations

from myhdl import Signal, modbv

from rtl.config import BonfireConfig


PIPELINE_SOURCE_NORMAL = 0
PIPELINE_SOURCE_PROGRAM_BUFFER = 1
PIPELINE_SOURCE_DEBUG_REGISTER = 2


class PipelineBoundaryEventBundle:
    """Debug-neutral events at the architectural pipeline boundary.

    The bundle deliberately describes both issue and terminal outcomes. A
    backend may have several operations in flight, but every terminal pulse
    describes exactly one accepted operation and carries the metadata needed
    by architectural consumers without inspecting pipeline stages.
    """

    def __init__(self, config: BonfireConfig) -> None:
        xlen = config.xlen

        # ``accepted`` qualifies issue metadata. ``valid`` qualifies the
        # metadata carried by a terminal event.
        self.accepted = Signal(bool(0))
        self.accepted_source = Signal(modbv(PIPELINE_SOURCE_NORMAL)[2:])
        self.accepted_pc = Signal(modbv(0)[xlen:])
        self.valid = Signal(bool(0))
        self.source = Signal(modbv(PIPELINE_SOURCE_NORMAL)[2:])

        self.terminal = Signal(bool(0))
        self.completed = Signal(bool(0))
        self.retired = Signal(bool(0))
        self.exception = Signal(bool(0))
        self.trap = Signal(bool(0))
        self.cancelled = Signal(bool(0))
        self.killed = Signal(bool(0))

        self.instruction_pc = Signal(modbv(0)[xlen:])
        self.next_pc = Signal(modbv(config.reset_address)[xlen:])

        self.redirect = Signal(bool(0))
        self.redirect_pc = Signal(modbv(0)[xlen:])
        self.register_write = Signal(bool(0))
        self.register_address = Signal(modbv(0)[5:])
        self.register_data = Signal(modbv(0)[xlen:])
        self.store_commit = Signal(bool(0))

        self.pipeline_empty = Signal(bool(1))
        self.drained = Signal(bool(1))

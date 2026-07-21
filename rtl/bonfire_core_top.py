"""
Bonfire Core toplevel
(c) 2019,2020 The Bonfire Project
License: See LICENSE
"""

from __future__ import annotations, print_function

from typing import Any

from myhdl import *

from rtl.simple_pipeline import *
from rtl.pipelined_backend import PipelinedBackend
from rtl.fetch import FetchUnit
from rtl import config
from rtl.bonfire_interfaces import ControlBundle, DbusBundle, DebugOutputBundle
from rtl.config import BonfireConfig
from rtl.debug import DmiBundle, DebugModuleInterface, DebugModuleRegisterBundle
from rtl.type_aliases import BitSignal

class BonfireCoreTop:
    def __init__(self, config: BonfireConfig = config.BonfireConfig()) -> None:
        self.config: BonfireConfig = config
        assert config.pipeline_length in (3, 4, 5), "pipeline_length must be 3, 4 or 5"
        assert not config.writeback_bypass or config.pipeline_length in (4, 5), \
            "writeback_bypass requires pipeline_length 4 or 5"
        assert not config.registered_dbus_feedback or config.registered_read_stage, \
            "registered_dbus_feedback requires registered_read_stage"
        self.fetch: FetchUnit = FetchUnit(config=config)
        self.backend_fetch_input: FetchInputBundle = FetchInputBundle(config=config)
        self.backend_fetch_output: BackendOutputBundle = BackendOutputBundle(config=config)
        if config.pipeline_length == 3:
            self.backend = SimpleBackend(config=config)
        else:
            self.backend = PipelinedBackend(config=config)
        if config.enableDebugModule:
            self.dmi: DebugModuleInterface = DebugModuleInterface(config)
            self.debugRegs: DebugModuleRegisterBundle | None = DebugModuleRegisterBundle(config)
        else:
            self.debugRegs = None


    @block
    def createInstance(self, ibus: DbusBundle, dbus: DbusBundle, control: ControlBundle,
                       clock: BitSignal, reset: BitSignal, debug: DebugOutputBundle,
                       config: BonfireConfig | None = None,
                       debugTransportBundle: DmiBundle | None = None) -> Any:
        """
        ibus:  DbusBundle for Instruction Bus (read only)
        dbus:  DbusBundle for Data bus
        control:  ControlBundle
        clock: CPU Clock
        reset: Reset line
        debug: Optional Simulation Debug Interface 
        config: Bonfire Configuration object (legacy, optional)
        debugTransportBundle: Optional Debug Transport interface
        """

        i_fetch = self.fetch.SimpleFetchUnit(
            self.backend_fetch_input, ibus, clock, reset,
            debugRegisterBundle=self.debugRegs)
        i_backend = self.backend.backend(
            self.backend_fetch_input, self.fetch,
            dbus, clock, reset, self.backend_fetch_output, debug,
            debugRegisterBundle=self.debugRegs)

        if self.config.enableDebugModule:
            assert debugTransportBundle is not None, "enableDebugModule requires debugTransportBundle"
            i_dmi = self.dmi.dmi_interface(
                dtm=debugTransportBundle,
                debugRegs=self.debugRegs,
                clock=clock)


        """
        Wire feedback channel between frontend (fetch) and Backend 
        """
        @always_comb
        def comb():
            self.fetch.jump_dest_i.next=self.backend_fetch_output.jump_dest_o
            self.fetch.jump_i.next = self.backend_fetch_output.jump_o
            #self.fetch.stall_i.next = self.backend_fetch_output.busy_o


        return instances()

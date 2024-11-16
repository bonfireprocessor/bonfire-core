"""
Bonfire Core toplevel
(c) 2019,2020 The Bonfire Project
License: See LICENSE
"""

from __future__ import print_function

from myhdl import *

from rtl.simple_pipeline import *
from rtl.fetch import FetchUnit
from rtl import config 
from rtl import debugModule

class BonfireCoreTop:
    def __init__(self,config=config.BonfireConfig()):
        self.config=config
        self.fetch = FetchUnit(config=config)
        self.backend_fetch_input = FetchInputBundle(config=config)
        self.backend_fetch_output = BackendOutputBundle(config=config)
        self.backend = SimpleBackend(config=config)
        if config.enableDebugModule:
            self.dmi = debugModule.DMI(config)
            self.debugRegs=debugModule.DebugRegisterBundle(config)
        else:
            self.debugRegs=None    


    @block
    def createInstance(self,ibus,dbus,control,clock,reset,debug,debugTransportBundle=None):
        """
        ibus:  DbusBundle for Instruction Bus (read only)
        dbus:  DbusBundle for Data bus
        control:  ControlBundle
        clock: CPU Clock
        reset: Reset line
        debug: Optional Simulation Debug Interface 
        debugTransport : Debug Transport module interface
        """

        i_fetch = self.fetch.SimpleFetchUnit(self.backend_fetch_input,ibus,clock,reset,debugRegisterBundle=self.debugRegs)
        i_backend = self.backend.backend(
                    fetchBundle=self.backend_fetch_input,
                    frontEnd=self.fetch,
                    databus=dbus,clock=clock,reset=reset,
                    out=self.backend_fetch_output,
                    debugport=debug,
                    debugRegisterBundle=self.debugRegs)


        if self.config.enableDebugModule:
            i_dmi = self.dmi.DMI_interface(dtm=debugTransportBundle,
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
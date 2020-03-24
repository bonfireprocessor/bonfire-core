"""
Bonfire Core toplevel
(c) 2019,2020 The Bonfire Project
License: See LICENSE
"""

from __future__ import print_function

from myhdl import *

from simple_pipeline import *
from fetch import FetchUnit
import config 

class BonfireCoreTop:
    def __init__(self,config=config.BonfireConfig()):
        self.config=config
        self.fetch = FetchUnit(config=config)
        self.backend_fetch_input = FetchInputBundle(config=config)
        self.backend_fetch_output = BackendOutputBundle(config=config)
        self.backend = SimpleBackend(config=config)


    @block
    def createInstance(self,ibus,dbus,control,clock,reset,debug,config):
        """
        ibus:  DbusBundle for Instruction Bus (read only)
        dbus:  DbusBundle for Data bus
        control:  ControlBundle
        clock: CPU Clock
        reset: Reset line
        debug: Optional Simulation Debug Interface 
        config: Bonfire Configuration object
        """

        i_fetch = self.fetch.SimpleFetchUnit(self.backend_fetch_input,ibus,clock,reset)
        i_backend = self.backend.backend(self.backend_fetch_input,self.fetch,
                    dbus,clock,reset,self.backend_fetch_output,debug)


        """
        Wire feedback channel between frontend (fetch) and Backend 
        """
        @always_comb
        def comb():
            self.fetch.jump_dest_i.next=self.backend_fetch_output.jump_dest_o
            self.fetch.jump_i.next = self.backend_fetch_output.jump_o
            #self.fetch.stall_i.next = self.backend_fetch_output.busy_o


        return instances()
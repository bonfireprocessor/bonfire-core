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


@block
def bonfore_core_top(ibus,dbus,control,clock,reset,debug,config):
    """
    ibus:  DbusBundle for Instruction Bus (read only)
    dbus:  DbusBundle for Data bus
    control:  ControlBundle
    clock: CPU Clock
    reset: Reset line
    debug: Optional Simulation Debug Interface 
    config: Bonfire Configuration object
    """

    fetch = FetchUnit(config=config)
    backend_fetch_input = FetchInputBundle(config=config)
    backend_fetch_output = BackendOutputBundle(config=config)
    backend = SimpleBackend(config=config)

    i_fetch = fetch.SimpleFetchUnit(backend_fetch_input,ibus,clock,reset)
    i_backend = backend.backend(backend_fetch_input,dbus,clock,reset,backend_fetch_output,debug)


    """
    Wire feedback channel between frontend (fetch) and Backend 
    """
    @always_comb
    def comb():
        fetch.jump_dest_i.next=backend_fetch_output.jump_dest_o
        fetch.jump_i.next = backend_fetch_output.jump_o
        fetch.stall_i.next = backend_fetch_output.busy_o



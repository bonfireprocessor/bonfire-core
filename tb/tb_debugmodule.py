"""
Bonfire Core Simulation Debug Server
(c) 2019,2020 The Bonfire Project
License: See LICENSE
"""


from __future__ import print_function

from myhdl import *
from dmi_api.debug_api import DebugAPISim

# Test Stimulus for debug interface


def tb_halt_resume(dtm_bundle,clock):
    """
    dtm_bundle: AbstractDebugTransportBundle
    clock: clock
    """

    api=DebugAPISim(dtm_bundle=dtm_bundle,clock=clock)

    for i in range(0,5):
        yield clock.posedge

    yield api.halt()

    print("core halted")

    for i in range(0,10):
        yield clock.posedge


    yield api.resume()

    print("Core resumed")




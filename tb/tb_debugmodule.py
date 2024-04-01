"""
Bonfire Core Simulation Debug Server
(c) 2019,2020 The Bonfire Project
License: See LICENSE
"""


from __future__ import print_function

from myhdl import *
from dmi_api.debug_api import DebugAPISim
from tb.disassemble import abi_name

# Test Stimulus for debug interface

@block
def tb_halt_resume(dtm_bundle,clock):
    """
    dtm_bundle: AbstractDebugTransportBundle
    clock: clock
    """

    @instance
    def test():
        api=DebugAPISim(dtm_bundle=dtm_bundle,clock=clock)

        for i in range(0,5):
            yield clock.posedge

        yield api.halt()
        print("@{}ns core halted".format(now()))

        for i in range(1,32):
            yield api.readGPR(regno=i)
            print("Reg {}: {}".format(abi_name(i),hex(api.result)))

        for i in range(0,10):
            yield clock.posedge


        yield api.resume()
        print("@{}ns core resumed".format(now()))

    return instances()    




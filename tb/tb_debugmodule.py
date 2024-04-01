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

    def check_reg(api,regno,check_value):
        yield api.readGPR(regno=regno)
        assert api.result == check_value,"check_reg failure {} {}".format(api.result,check_value)
        print("@{}ns: Expected reg value: {}".format(now(),hex(api.result)))



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

        print("Reg Write Test")
        
        yield api.readGPR(regno=1)
        reg_save=api.result+0
        print("@{}ns Save backup of register x1: {}".format(now(),hex(reg_save)))
        yield api.writeGPR(regno=1,value=0xdeadbeef)
        yield check_reg(api,regno=1,check_value=0xdeadbeef)
        yield api.writeGPR(regno=1,value=reg_save)
        yield check_reg(api,regno=1,check_value=reg_save)



        yield api.resume()
        print("@{}ns core resumed".format(now()))

    return instances()    




"""
Bonfire Core Simulation Debug Server
(c) 2019,2020 The Bonfire Project
License: See LICENSE
"""


from __future__ import print_function

from myhdl import *
from dmi_api.debug_api import DebugAPISim
from tb.disassemble import abi_name
from rtl.instructions import CSRAdr

# Test Stimulus for debug interface

@block
def tb_halt_resume(dtm_bundle,clock):
    """
    dtm_bundle: AbstractDebugTransportBundle
    clock: clock
    """

    def check_gpr(api,regno,check_value):
        yield api.readGPR(regno=regno)
        assert api.result == check_value,"check_gpr failure result: {} expected: {}".format(api.result,check_value)
        print("@{}ns: Expected reg value: {}".format(now(),hex(api.result)))


    @instance
    def test():
        api=DebugAPISim(dtm_bundle=dtm_bundle,clock=clock)

        for i in range(0,5):
            yield clock.posedge

        yield api.halt()
        print("@{}ns core halted".format(now()))

        yield api.readReg(regno=0x700 | CSRAdr.dpc)
        print("Reg dpc: {}".format(hex(api.result)))    

        for i in range(1,32):
            yield api.readGPR(regno=i)
            print("Reg {}: {}".format(abi_name(i),hex(api.result)))

      

        print("Reg Write Test")
        
        yield api.readGPR(regno=1)
        reg_save=api.result+0
        print("@{}ns Save backup of register x1: {}".format(now(),hex(reg_save)))
        yield api.writeGPR(regno=1,value=0xdeadbeef)
        yield check_gpr(api,regno=1,check_value=0xdeadbeef)
        yield api.writeGPR(regno=1,value=reg_save)
        yield check_gpr(api,regno=1,check_value=reg_save)


        print("@{}ns Check r/w to progbuf0".format(now()))
        opcode=0x00a00593 # li	a1,10
        #opcode=0x00b42223    # sw a1,4(s0)
        yield api.dmi_write(0x20,opcode) 
        yield api.dmi_read(0x20)
        assert api.result == opcode
        print("@{}ns Exec progbuf".format(now()))
        yield api.readGPR(regno=11,postexec=True) # Read Reg a1 (x11) and exec progbuf
        save_a1=api.result+0
        print("@{}ns progbuf exec completed".format(now()))
        yield check_gpr(api,regno=11,check_value=10) # Progbuf comand should have set reg a1 t0 10
        yield api.writeGPR(regno=11,value=save_a1) 
        yield check_gpr(api,regno=11,check_value=save_a1) # Check that register is restored to orignal value


        yield api.resume()
        print("@{}ns core resumed".format(now()))

    return instances()    




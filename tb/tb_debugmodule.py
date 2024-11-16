"""
Bonfire Core Simulation Debug Server
(c) 2019,2020 The Bonfire Project
License: See LICENSE

Remark: For Test to be sucessfull Test code debug.hex must be loaded
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

    def check_cmd_result(api,check_value,text=""):
        assert api.cmd_result() == check_value,"{} result: {} expected: {}".format(text,hex(api.cmd_result()),hex(check_value))
        print("@{}ns: Expected value: {}".format(now(),hex(api.cmd_result())))


    def check_gpr(api,regno,check_value):
        yield api.readGPR(regno=regno)
        assert api.cmd_result() == check_value,"check_gpr failure result: {} expected: {}".format(hex(api.cmd_result()),hex(check_value))
        print("@{}ns: Expected reg value: {}".format(now(),hex(api.cmd_result())))


    @instance
    def test():
        api=DebugAPISim(dtm_bundle=dtm_bundle,clock=clock)

        for i in range(0,5):
            yield clock.posedge

        yield api.halt()
        print("@{}ns core halted".format(now()))

        yield api.readReg(regno=0x700 | CSRAdr.dpc)
        print("Reg dpc: {}".format(hex(api.cmd_result())))    

        gpr_save = [0]

        # Read and save gprs
        for i in range(1,32):
            yield api.readGPR(regno=i)
            gpr_save.append(api.cmd_result())
            print("Reg {}: {}".format(abi_name(i),hex(api.cmd_result())))

      
        assert(gpr_save[10]==0) # a0 should be 0 

        print("Reg Write Test")
        yield api.writeGPR(regno=1,value=0xdeadbeef)
        yield check_gpr(api,regno=1,check_value=0xdeadbeef)
        

        print("@{}ns Check r/w to progbuf0".format(now()))
     
        opcode=0x00100513 # li	a0,1
     
        yield api.dmi_write(0x20,opcode) 
        yield api.dmi_read(0x20)
        assert api.cmd_result() == opcode
        print("@{}ns Exec progbuf".format(now()))
        yield api.readReg(transfer=False,postexec=True) # exec progbuf
      
        print("@{}ns progbuf exec completed".format(now()))
        yield check_gpr(api,regno=10,check_value=1) # Progbuf comand should have set reg a1 to 1
        

        print(f"@{now()}ns Memory read test")
        yield api.readMemory(memadr=0x4)
        print(f"Memory address 4 contains: {hex(api.cmd_result())}")
        mem_save=api.cmd_result()

        print(f"@{now()}ns Memory write test")
        yield api.writeMemory(memadr=0x4,memvalue=0xdeadbeef)
       
        
        print(f"@{now()}ns Memory write check")
        yield api.readMemory(memadr=0x4)
        print(f"Memory address 4 contains: {hex(api.cmd_result())}")
        check_cmd_result(api,0xdeadbeef,"Mem address 4")

        print(f"@{now()}ns Restoring old mem value")
        yield api.writeMemory(memadr=0x4,memvalue=mem_save)
        yield api.readMemory(memadr=0x4)
        check_cmd_result(api,mem_save,"Restore mem value check")

        gpr_save[10] = 1 # Patch a1 to 1 
        print(f"@{now()}ns Restoring all gprs")
        for i in range(1,32):

            yield api.writeGPR(regno=i,value=gpr_save[i])
            yield check_gpr(api,regno=i,check_value=gpr_save[i])
            print("Reg {}: {}".format(abi_name(i),hex(api.cmd_result())))

        yield api.writeReg(regno=0x700 | CSRAdr.dpc,value=0x10) # Code should continue at address 0x10

        yield api.resume()
        print("@{}ns core resumed".format(now()))

    return instances()    




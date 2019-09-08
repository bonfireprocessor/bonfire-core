from myhdl import *

from rtl.regfile import * 
from ClkDirver import *


clock=Signal(bool(0))
reset = ResetSignal(0, active=1, isasync=False)


reg_portA = RFReadPort()
reg_portB = RFReadPort()
reg_writePort = RFWritePort()


@block
def tb():
    clk_driver= ClkDriver(clock)

    inst=RegisterFile(clock,reg_portA,reg_portB,reg_writePort)
    inst.convert(hdl='VHDL',std_logic_ports=True,path='vhdl_gen', name="regfile" )

    @instance
    def stimulus():
        yield clock.posedge

        for i in range(0,32):
            reg_writePort.wa.next = i 
            reg_portA.ra.next = i
            reg_portB.ra.next = i 
            reg_writePort.wd.next = 0x55aa0000 | i 
            reg_writePort.we.next = 1
            yield clock.posedge 

        reg_writePort.we.next = 0
        for i in range(0,32):
            reg_portA.ra.next = i
            reg_portB.ra.next = i 
            yield clock.posedge
            print reg_portA.rd, reg_portB.rd 


        print "Simulation finished"
        raise StopSimulation    

    return instances()
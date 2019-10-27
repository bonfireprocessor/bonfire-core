from myhdl import *

from rtl.loadstore import *
from ClkDriver import *

from rtl.instructions import LoadFunct3, StoreFunct3
from rtl import config

ram_size=256



@block
def tb(config=config.BonfireConfig(),test_conversion=False):

    config.loadstore_outstanding=2

    clock=Signal(bool(0))
    reset = ResetSignal(0, active=1, isasync=False)

    clk_driver= ClkDriver(clock)

   
    bus = DbusBundle(config)
    ls = LoadStoreBundle(config)

    dut=ls.LoadStoreUnit(bus,clock,reset)


    ram = [Signal(modbv(0)[32:]) for ii in range(0, ram_size)]


    @always_seq(clock.posedge,reset=reset)
    def bus_slave():

        bus.ack_i.next=False 

        if bus.en_o:
            print("Ack Cycle:",now())
            if bus.we_o==0:
                bus.db_rd.next = ram[bus.adr_o[32:2]]
                print("Read from {} : {}".format(bus.adr_o,ram[bus.adr_o[32:2]]) )
            else:
                for i in range(len(bus.we_o)):
                    if bus.we_o[i]:
                        low = i * 8
                        high = low+8
                        ram[bus.adr_o[32:2]][high:low].next = bus.db_wr[high:low]
                print("Write: mask: {}, adr: {}, value {}".format(bin(bus.we_o),bus.adr_o,bus.db_wr))
            bus.ack_i.next = True
          

    @always_seq(clock.posedge,reset=reset)
    def collect():
        if ls.valid_o:
            print("Cycle Terminated")
            raise StopSimulation
    


    @instance
    def stimulus():
        yield clock.posedge
        print(now())
        ls.en_i.next = True
        ls.funct3_i.next = StoreFunct3.RV32_F3_SW
        ls.store_i.next = True
        ls.op1_i.next = 0x8
        ls.displacement_i.next= -4
        ls.op2_i.next = 0xdeadbeef
        ls.rd_i.next = 5

        yield clock.posedge
        print(now())

    return instances()

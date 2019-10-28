from __future__ import print_function

from myhdl import *

from rtl.loadstore import *
from ClkDriver import *

from rtl.instructions import LoadFunct3, StoreFunct3
from rtl import config

ram_size=256

store_words= (0xdeadbeef,0x55aaeeff,0x12345678,0x0055ff00,0xaabbccdd)

stop_condition = len(store_words)*2


@block
def tb(config=config.BonfireConfig(),test_conversion=False):

    config.loadstore_outstanding=1

    clock=Signal(bool(0))
    reset = ResetSignal(0, active=1, isasync=False)

    clk_driver= ClkDriver(clock)

   
    bus = DbusBundle(config)
    ls = LoadStoreBundle(config)

    dut=ls.LoadStoreUnit(bus,clock,reset)


    ram = [Signal(modbv(0)[32:]) for ii in range(0, ram_size)]

    cnt = Signal(intbv(0))

    @always_seq(clock.posedge,reset=reset)
    def bus_slave():

        bus.ack_i.next=False 
        
        if bus.en_o:
            print("Ack Cycle:",now())
            if bus.we_o==0:
                bus.db_rd.next = ram[bus.adr_o[32:2]]
                print("Read from {} : {}".format(bus.adr_o,ram[bus.adr_o[32:2]]) )
            else:
                wd=modbv(0)[32:]
                wd[:] = ram[bus.adr_o[32:2]]
                for i in range(len(bus.we_o)):         
                   
                    if bus.we_o[i]:
                        low = i * 8
                        high = low+8
                        wd[high:low] = bus.db_wr[high:low]

                ram[bus.adr_o[32:2]].next = wd 

                print("Write: mask: {}, adr: {}, value {}".format(bin(bus.we_o),bus.adr_o,bus.db_wr))
            bus.ack_i.next = True
           
            if cnt == stop_condition:
                raise StopSimulation
            else:
                cnt.next = cnt + 1   
          

    # @always_seq(clock.posedge,reset=reset)
    # def collect():
    #     if ls.valid_o:
    #         print("Cycle Terminated")
    #         raise StopSimulation
    

    fetch_index=Signal(intbv(0))
    write_feed = Signal(bool(0))

    @always_seq(clock.posedge,reset=reset)
    def feed():
        if write_feed and not ls.busy_o:
            ls.en_i.next = True
            ls.displacement_i.next = fetch_index * 4
            ls.op2_i.next = store_words[fetch_index]
            if fetch_index<len(store_words)-1:
                fetch_index.next = fetch_index + 1
            else:
                fetch_index.next = 0     


    @instance
    def stimulus():
        yield clock.posedge
       
        ls.funct3_i.next = StoreFunct3.RV32_F3_SW
        ls.store_i.next = True
        ls.op1_i.next = 0
        #ls.op2_i.next = 0xdeadbeef
        ls.rd_i.next = 5
        write_feed.next=True 

       

    return instances()

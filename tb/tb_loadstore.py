from __future__ import print_function

from myhdl import *

from rtl.loadstore import *
from ClkDriver import *

from rtl.instructions import LoadFunct3, StoreFunct3
from rtl import config

ram_size=256

store_words= (0xdeadbeef,0x55aaeeff,0x12345678,0x0055ff00,0xaabbccdd)



@block
def tb(config=config.BonfireConfig(),test_conversion=False):

    print("loadstore with outstanding=",config.loadstore_outstanding)
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
           
          

    
    fetch_index = Signal(intbv(0))
    write_feed = Signal(bool(0))

    
    @always_seq(clock.posedge,reset=reset)
    def do_write_feed():
        if write_feed and fetch_index<len(store_words):
            ls.en_i.next = True
            if not ls.busy_o:
                ls.displacement_i.next = fetch_index * 4
                ls.op2_i.next = store_words[fetch_index]
                fetch_index.next = fetch_index + 1

        else:
            if not ls.busy_o:   
                ls.en_i.next=False




    @always_seq(clock.posedge,reset=reset)
    def stop_sim():
        if ram[4]==store_words[len(store_words)-1]:
            raise StopSimulation



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

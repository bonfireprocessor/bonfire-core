from __future__ import print_function

from myhdl import *

from tb.ClkDriver import *

from rtl.cache.cache_way import TagDataBundle
from rtl.cache.tag_ram import tag_ram_instance 
from rtl.cache.config import CacheConfig

@block
def tb(test_conversion=False):

    conf = CacheConfig()

    clock=Signal(bool(0))
    reset = ResetSignal(0, active=1, isasync=False)

    clk_driver= ClkDriver(clock)

    t_in = TagDataBundle(10)
    t_out = TagDataBundle(10)

    we = Signal(bool(0))
    adr = Signal(modbv(0)[conf.line_select_adr_bits:])
    
    t_r_i = tag_ram_instance(t_in,t_out,we,adr,clock,reset,conf)
    if test_conversion:
        t_r_i.convert(hdl='VHDL',std_logic_ports=True,path='vhdl_gen', name="tb_cache")


    @instance
    def stimulus():

        yield clock.posedge

        # Write data
        we.next = True
        for i in range(0,16):
            adr.next = i  
            t_in.address.next = i
            t_in.valid.next = True
            t_in.dirty.next = False

            yield clock.posedge 


        fs = "address: {address}, valid:{valid}, dirty:{dirty} @{adr}"
        we.next = False
        adr.next = 0
        yield clock.posedge

        for i in range(0,16):
            adr.next = i  
            yield clock.posedge
            print(fs.format(adr=adr,**t_out.__dict__))   
            


        print ("Simulation finished")
        raise StopSimulation

    return instances()
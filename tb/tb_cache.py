from __future__ import print_function

from myhdl import *

from tb.ClkDriver import *



@block
def tb_tagram(test_conversion=False):

    from rtl.cache.cache_way import TagDataBundle
    from rtl.cache.tag_ram import tag_ram_instance 
    from rtl.cache.config import CacheConfig

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
        t_r_i.convert(hdl='VHDL',std_logic_ports=True,path='vhdl_gen', name="tag_ram")


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

@block
def tb_cache_way(test_conversion=False):
    from rtl.cache.cache_way import cache_way_instance, CacheWayBundle
    from rtl.cache.config import CacheConfig

    conf = CacheConfig()
    conf.print_config()

    clock = Signal(bool(0))
    clk_driver= ClkDriver(clock)
    reset = ResetSignal(0, active=1, isasync=False)

    w = CacheWayBundle(conf)

    cw_inst = cache_way_instance(w,clock,reset,conf)
    if test_conversion:
        cw_inst.convert(hdl='VHDL',std_logic_ports=True,path='vhdl_gen', name="cache_way")


    def miss_and_update(adr):
        print("tag miss and update with adr:{}".format(adr))
        conf.print_address(adr)
        w.adr.next = adr
        w.en.next = 1
        yield clock.posedge
        # wait for response
        while not (w.hit or w.miss):
            yield clock.posedge
        assert w.miss and not w.hit, "Miss=1 hit=0 expected"
        assert not w.tag_valid
        assert not w.dirty_miss
        # Write Tag
        w.we.next = True
        w.valid.next = True
        w.dirty.next = True
        yield clock.posedge
        w.we.next = False

        yield clock.posedge

        assert w.tag_valid, "after tag update: tag_valid should be set"
        assert w.hit, "after tag update: hit should be set"
        assert not w.miss, "after tag update: miss should not be set"
        print("OK")


    @instance
    def stimulus():


        yield clock.posedge
        for i in range(0,16): #  conf.tag_ram_size):
            adr = conf.create_address(0,i,0)
            yield miss_and_update(adr)
        
        raise StopSimulation

    return instances()    
            
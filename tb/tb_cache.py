from __future__ import print_function

from myhdl import *

from tb.ClkDriver import *

from rtl.cache.config import CacheConfig

@block
def tb_tagram(test_conversion=False):

    from rtl.cache.cache_way import TagDataBundle
    from rtl.cache.tag_ram import tag_ram_instance 
    
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

    cw_inst = cache_way_instance(w,clock,reset)
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


@block
def tb_cache(test_conversion=False,config=CacheConfig()):

    from rtl.cache.cache import CacheMasterWishboneBundle, CacheControlBundle, cache_instance
    from rtl.bonfire_interfaces import DbusBundle
    from tb.sim_wb_burst_ram import ram_interface

    clock=Signal(bool(0))
    reset = ResetSignal(0, active=1, isasync=False)
    clk_driver= ClkDriver(clock)

    # our simulated RAM is four times the cache size, this is enough for write testing...
    ram = [Signal(modbv(0)[config.master_data_width:]) for ii in range (0,config.cache_size_m_words*4)]

    wb_master = CacheMasterWishboneBundle(config)
    db_slave = DbusBundle(len=32)

    pattern_mode = Signal(bool(True))

    ram_i = ram_interface(ram,wb_master,pattern_mode,clock,config)
    c_i = cache_instance(db_slave,wb_master,clock,reset,config)



    def db_read(address):
        yield clock.posedge

        db_slave.en_o.next = True
        db_slave.we_o.next = 0
        db_slave.adr_o.next = address
        while not db_slave.ack_i:
            yield clock.posedge
        db_slave.en_o.next = False
        
    loop_success = False    

    def read_loop(start_adr,length):
        loop_success = False
        for i in range(0,length):
            adr = start_adr + i *4
            yield db_read(adr)
            print(db_slave.db_rd)
            assert db_slave.db_rd == adr, "Read failure at address {}: {}".format(hex(adr),db_slave.db_rd)
               

    @instance
    def stimulus():
        yield read_loop(0,16)

        print(db_slave.db_rd)
        yield clock.posedge
        raise StopSimulation



    return instances()

from __future__ import print_function

from myhdl import *

from tb.ClkDriver import *

from rtl.cache.config import CacheConfig


def print_t(s):
    print("@{}: {}".format(now(),s))

@block
def tb_tagram(test_conversion=False):

    from rtl.cache.cache_way import TagDataBundle
    from rtl.cache.tag_ram import tag_ram_instance

    conf = CacheConfig(**kwargs)

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
def tb_cache(test_conversion=False,
                 master_data_width = 128,
                 line_size = 4, # Line size in MASTER_DATA_WIDTH  words
                 cache_size_m_words = 2048, # Cache Size in MASTER_DATA_WIDTH Bit words
                 address_bits = 30, #  Number of bits of chacheable address range
                 num_ways = 1, # Number of cache ways
                 pipelined = False,
                 verbose = False
            ):

    from rtl.cache.cache import CacheMasterWishboneBundle, CacheControlBundle, cache_instance
    from rtl.bonfire_interfaces import DbusBundle
    from tb.sim_wb_burst_ram import ram_interface

    config = CacheConfig(master_data_width=master_data_width,
                         line_size=line_size,
                         cache_size_m_words=cache_size_m_words,
                         address_bits=address_bits,
                         num_ways=num_ways)

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

    address_queue = []
    queue_len = Signal(intbv(0))
   


    @always(clock.posedge)
    def monitor_ack():

        if  db_slave.ack_i:
            ack_address = address_queue.pop(0)
            queue_len.next = len(address_queue)
            assert queue_len > 0, "ack raised on empy queue"
            if ack_address[2]=="r":               
                if verbose:
                    print_t("read_ack: {}:{}".format(ack_address[0],db_slave.db_rd))
                    
                if ack_address[1] != None:
                    assert db_slave.db_rd == ack_address[1], \
                      "@{}: read from {}, verify failed expected: {}, read:{}".format(now(),
                            hex(ack_address[0]), hex(ack_address[1]),db_slave.db_rd)
            else:
                if verbose:
                    print_t("write ack at {}:".format(ack_address[0]))
               
            assert not db_slave.stall_i, "@{} db_slave ack_i while stall_i raised".format(now())



    def db_read(address,verify=None,blocking=False): # pipelined read start, does not wait on ack

        db_slave.en_o.next = True
        db_slave.we_o.next = 0
        db_slave.adr_o.next = address
        address_queue.append((address,verify,"r"))
        queue_len.next = len(address_queue)
        yield clock.posedge
        # Block on stall
        while db_slave.stall_i:
            yield clock.posedge
        db_slave.en_o.next = False

        if blocking:
            while not db_slave.ack_i:
                yield clock.posedge


    def read_loop(start_adr,length,pipelined=False):

        print("Start loop at:")
        config.print_address(start_adr)

        for i in range(0,length):
            adr = modbv((start_adr + i) << 2)[32:]
            yield db_read(adr,adr,not pipelined)



    def db_write(address,data,blocking=False):
        yield clock.posedge

        db_slave.en_o.next = True
        db_slave.we_o.next = 0b1111
        db_slave.adr_o.next = address
        db_slave.db_wr.next = data
        address_queue.append((address,None,"w"))
        queue_len.next = len(address_queue)
        yield clock.posedge
        # Block on stall
        while db_slave.stall_i:
            yield clock.posedge

        db_slave.en_o.next = False
        db_slave.we_o.next = 0
        if blocking:
            while not db_slave.ack_i:
                yield clock.posedge
                db_slave.en_o.next = False # deassert en after first clock

            

    @instance
    def stimulus():
        config.print_config()
        line_size = 2**config.cl_bits_slave # Line size in slave words

        def loop_test(pipelined):
            print_t("Loop test pipelined" if pipelined else "Loop test" )
            for i in range(0,1):
                yield clock.posedge
                yield clock.posedge

                print_t("Read two lines")
                yield read_loop(config.create_address(0,0,0),line_size*2,pipelined)
                print_t("Read two lines with same line index, but different tag value")
                yield read_loop(config.create_address(1,0,0),line_size*2,pipelined)

            #print_t("Read from last line of cache")
            #yield read_loop(config.create_address(0,2**config.line_select_adr_bits-1,0),line_size,pipelined)

        def basic_write_test(pipelined):
            blocking = not pipelined

            pattern_mode.next = False
            yield clock.posedge
            print_t("Basic write test")
            yield db_write(0,0xdeadbeef,blocking)
            yield db_write(4,0xabcd8000,blocking)

            yield db_read(0,0xdeadbeef,blocking)
            yield db_read(4,0xabcd8000,blocking)
            print_t("Write back test")
            adr = config.create_address(1,0,0) << 2
            yield db_write(adr,0x55aa55ff,blocking)
            yield db_read(adr,0x55aa55ff,blocking)
            print_t("cross check")
            yield db_read(0,0xdeadbeef,blocking)



        yield loop_test(pipelined)
        yield basic_write_test(pipelined)

        yield clock.posedge
        raise StopSimulation



    return instances()

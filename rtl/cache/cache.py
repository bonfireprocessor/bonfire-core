"""
Bonfire Core Cache
(c) 2019,2020 The Bonfire Project
License: See LICENSE
"""
from myhdl import Signal,intbv,modbv, concat,  \
                  block,always_comb,always_seq, always, instances, enum, now

from rtl.util import int_log2


import rtl.cache.cache_way as cache_way
from  rtl.cache.config import CacheConfig
from rtl.cache.cache_ram import CacheRAMBundle,cache_ram_instance
from rtl.cache.cache_businterface import BusOutputBundle, BusInputBundle, cache_dbslave_connect
from rtl.bonfire_interfaces import Wishbone_master_bundle

class CacheControlBundle:
    def __init__(self):
        self.invalidate = Signal(bool(0)) # Trigger invalidation of the Cache
        self.invalidate_ack = Signal(bool(0)) # Asserted for one cycle when invalidation is complete
        # TODO: Add other control lines

class CacheMasterWishboneBundle(Wishbone_master_bundle):
    def __init__(self,config=CacheConfig()):
        Wishbone_master_bundle.__init__(self,
        adrHigh=32,
        adrLow=int_log2(config.master_width_bytes),
        dataWidth=config.master_data_width,
        b4_pipelined=False,
        bte_signals=True)



@block
def cache_instance(db_slave,master,clock,reset,config=CacheConfig()):
    """
    slave : DbusBundle - slave interface connected to the "CPU side" of the cache
    master: CacheMasterWishboneBundle - master interface connected to the "outer memory"
    control: CacheControlBundle - interface for cache control
    """

    # Checks
    assert config.num_ways == 1, "Cache Instance, currently only 1 way implemented"
    #assert config.master_data_width == master.xlen, "Master Bus Width must be equal config.master_data_width"

    # State engine
    t_wbm_state = enum('wb_idle','wb_burst_read','wb_burst_write','wb_finish','wb_retire')
    wbm_state = Signal(t_wbm_state.wb_idle)


    cache_offset_counter = Signal(modbv(0)[config.cl_bits:])
    master_offset_counter = Signal(modbv(0)[config.cl_bits:])
    slave_cache_we = Signal(bool(0))


    # Slave Interface
    bus_input = BusInputBundle(config,db_slave.xlen)
    bus_output = BusOutputBundle(config,db_slave.xlen)

    # Splitted slave adr
    slave_adr_splitted = cache_way.AddressBundle(config)
    s_adr_i = slave_adr_splitted.from_bit_vector(bus_input.slave_adr_slice)

    # Enable signal for master Wishbone bus
    wbm_enable = Signal(bool(0))

    # Cache RAM
    cache_ram = CacheRAMBundle(config)
    c_r_i = cache_ram_instance(cache_ram,clock)


    if config.num_ways == 1:
        tag_control = cache_way.CacheWayBundle(config)
        tc_i = cache_way.cache_way_instance(tag_control,clock,reset)

    else:
        pass # TODO: Add support for num_ways > 1


    s_i = cache_dbslave_connect(db_slave,bus_input,bus_output,tag_control.hit,clock,reset,config)

    # @always(clock.posedge)
    # def debug_output():

    #     if slave.en_o and tag_control.hit and not slave_rd_ack:
    #         print("@{} Cache hit for address: {}, cache RAM adr:{}".format(now(),slave_adr_slice,cache_ram.slave_adr))
    #         assert tag_control.buffer_index == slave_adr_splitted.tag_index, "Tag Index mismatch"
    #         slave_adr_splitted.debug_print()



    # Cache RAM Bus Multiplexers
    if config.mux_size == 1:
         @always_comb
         def db_mux_1():

             cache_ram.slave_db_wr.next = bus_input.slave_write
             cache_ram.slave_we.next = bus_input.slave_we

             bus_output.slave_read.next = cache_ram.slave_db_rd
             cache_ram.slave_adr.next = concat(slave_adr_splitted.tag_index,slave_adr_splitted.word_index)
    else:
        # Calcluate slave bus address bits for selecting the right 32 slice
        # from the master bus
        mx_low = 0
        mx_high = mx_low + int_log2(config.mux_size)
        slave_db_mux_reg = Signal(modbv(0)[int_log2(config.mux_size):])

        # Calculate bit range from word_index to select the cache word of a line in cache ram

        wi_low = mx_high
        wi_high = wi_low + config.cl_bits

        @always(clock.posedge)
        def db_mux_sync():
            if tag_control.hit and  bus_input.slave_en:
                slave_db_mux_reg.next = bus_input.slave_adr_slice[mx_high :mx_low]


        @always_comb
        def db_mux_n():
            # Data bus multiplexer
            bus_output.slave_read.next = 0 # Avoid latch
            for i in range(0,config.mux_size):
                if slave_db_mux_reg == i:
                    # Databus Multiplexer, select the 32 Bit word from the cache ram word.
                    bus_output.slave_read.next = cache_ram.slave_db_rd[(i+1)*32:(i*32)]

            cache_ram.slave_db_wr.next = 0
            for i in range(0,config.mux_size):
                # For writing the Slave bus can just be demutiplexed n times
                # Write Enable is done on byte lane level
                cache_ram.slave_db_wr.next[(i+1)*32:i*32] = bus_input.slave_write

                # Write enable line multiplexer
                if bus_input.slave_adr_slice[mx_high :mx_low] == i:
                    cache_ram.slave_we.next[(i+1)*4:i*4] = bus_input.slave_we
                else:
                    cache_ram.slave_we.next[(i+1)*4:i*4] = 0

            # Slave address bus
            cache_ram.slave_adr.next = concat(slave_adr_splitted.tag_index,slave_adr_splitted.word_index[wi_high:wi_low])

    @always_comb
    def proc_slave_write_enable():
        if bus_input.slave_en and bus_input.slave_we != 0 and tag_control.hit:
            slave_cache_we.next = True # slave.en_o and slave.we_o != 0 and tag_control.hit
        else:
            slave_cache_we.next = False

    @always_comb
    def cache_control_comb():

        # Tag Control

        tag_control.en.next = bus_input.slave_en
        tag_control.we.next = (master.wbm_ack_i and wbm_state==t_wbm_state.wb_finish) or slave_cache_we
        tag_control.dirty.next = slave_cache_we
        tag_control.valid.next = not tag_control.dirty_miss
        tag_control.adr.next = bus_input.slave_adr_slice

        # Cache RAM control signals
        # Slave side
        cache_ram.slave_en.next = tag_control.hit and bus_input.slave_en

        # Master side
        cache_ram.master_en.next = ( master.wbm_ack_i and wbm_enable ) or \
                                   ( tag_control.dirty_miss and wbm_state == t_wbm_state.wb_idle )

        cache_ram.master_we.next = master.wbm_ack_i and not tag_control.dirty_miss
        cache_ram.master_db_wr.next = master.wbm_db_i

        if tag_control.dirty_miss:
            cache_ram.master_adr.next = concat(tag_control.buffer_index,cache_offset_counter)
        else:
            cache_ram.master_adr.next = concat(tag_control.tag_index,master_offset_counter)



        # Master bus
        master.wbm_cyc_o.next = wbm_enable
        master.wbm_stb_o.next = wbm_enable
        master.wbm_db_o.next = cache_ram.master_db_rd


    @always_comb
    def proc_master_adr():

        if tag_control.dirty_miss:
            master.wbm_adr_o.next = concat(tag_control.tag_value,
                                    tag_control.buffer_index,master_offset_counter)
        else:
            master.wbm_adr_o.next = concat(slave_adr_splitted.tag_value,
                                    slave_adr_splitted.tag_index,
                                    master_offset_counter)


    # State engine for cache refill/writeback
    @always_seq(clock.posedge,reset)
    def master_rw():

        if wbm_state == t_wbm_state.wb_idle:
            if tag_control.miss and not tag_control.hit:
                wbm_enable.next = True
                for i in range(0,len(master.wbm_sel_o)):
                    master.wbm_sel_o.next[i] = True

                master.wbm_cti_o.next = 0b010
                master.wbm_bte_o.next = 0b00
                if tag_control.dirty_miss:
                    cache_offset_counter.next = master_offset_counter + 1
                    master.wbm_we_o.next = True
                    wbm_state.next = t_wbm_state.wb_burst_write
                else:
                    master.wbm_we_o.next = False
                    wbm_state.next = t_wbm_state.wb_burst_read


        elif wbm_state == t_wbm_state.wb_burst_read or wbm_state == t_wbm_state.wb_burst_write:
            n = master_offset_counter + 1
            if master.wbm_ack_i:
                if n == master_offset_counter.max-1:
                    master.wbm_cti_o.next = 0b111
                    wbm_state.next = t_wbm_state.wb_finish
                master_offset_counter.next = n
                cache_offset_counter.next = n + 1

        elif wbm_state == t_wbm_state.wb_finish:
            if master.wbm_ack_i:
                wbm_enable.next = False
                master.wbm_we_o.next = False
                master_offset_counter.next = 0
                cache_offset_counter.next = 0
                wbm_state.next = t_wbm_state.wb_retire

        else:
            assert wbm_state == t_wbm_state.wb_retire
            wbm_state.next = t_wbm_state.wb_idle





    return instances()
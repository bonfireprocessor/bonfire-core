"""
Bonfire Core Cache
(c) 2019,2020 The Bonfire Project
License: See LICENSE
"""
from myhdl import Signal,intbv,modbv,ConcatSignal, \
                  block,always_comb,always_seq,instances, enum, now

from rtl.util import int_log2

import rtl.cache.cache_way as cache_way
from  rtl.cache.config import CacheConfig
from rtl.cache.cache_ram import CacheRAMBundle,cache_ram_instance
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
        b4_pipelined=True,
        bte_signals=True)



@block
def cache_instance(slave,master,clock,reset,config=CacheConfig()):
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

    # Constants
    slave_adr_low = int_log2(slave.xlen // 8)
    slave_adr_high = slave_adr_low + config.set_adr_bits

    # local Signals
    write_back_enable = Signal(bool(0))
    cache_offset_counter = Signal(intbv(0,max=config.line_size))
    master_offset_counter = Signal(intbv(0,max=config.line_size))

    slave_rd_ack = Signal(bool(0))
    slave_write_enable = Signal(bool(0))


    wbm_enable = Signal(bool(0)) # Enable signal for master Wishbone bus


    # Cache RAM
    cache_ram = CacheRAMBundle(config)
    c_r_i = cache_ram_instance(cache_ram,clock)


    if config.num_ways == 1:
        tag_control = cache_way.CacheWayBundle(config=config)
        tc_i = cache_way.cache_way_instance(tag_control,clock,reset)

        @always_comb
        def comb():
            cache_ram.slave_adr.next = slave.adr_o[slave_adr_high:slave_adr_low]

            if write_back_enable:
                cache_ram.master_adr.next = ConcatSignal(tag_control.buffer_index,cache_offset_counter)
            else:
                cache_ram.master_adr.next = ConcatSignal(tag_control.tag_index,master_offset_counter)
    else:
        pass # TODO: Add support for num_ways > 1

    # Cache RAM Bus Multiplexers
    if config.mux_size == 1:
         @always_comb
         def db_mux_1():
             cache_ram.slave_db_wr.next =  slave.db_wr
             cache_ram.slave_we.next = slave.we_o
             slave.db_rd.next = cache_ram.slave_db_rd
    else:
        # Calcluate slave bus address bits for selecting the right 32 slice
        # from the master bus
        mx_low = slave_adr_low
        mx_high = slave_adr_low + int_log2(config.mux_size)

        @always_comb
        def db_mux_n():
            # Data bus multiplexer
            for i in range(0,config.mux_size):
                # For writing the Slave bus can just be demutiplexed n times
                # Write Enable is done on byte lane level
                cache_ram.slave_db_wr[(i+1)*32:i*32].next = slave.db_wr

                if slave.adr_o[mx_high :mx_low] == i:
                     # Write enable line multiplexer
                    cache_ram.slave_we[(i+1)*4:i*4].next = slave.we_o
                    # Databus Multiplexer, select the 32 Bit word from the cache ram word.
                    slave.db_rd.next = cache_ram.slave_db_rd[(i+1)*32:(i*32)]
                else:
                    cache_ram.slave_we[(i+1)*4:i*4].next = 0



    @always_comb
    def cache_control_comb():

        # Cache RAM control signals
        # Slave side
        cache_ram.slave_en.next = tag_control.hit and slave.en_o
        # Master side
        cache_ram.master_en.next = ( master.wbm_ack_i and wbm_enable ) or \
                                   ( write_back_enable and wbm_state == t_wbm_state.wb_idle )

        cache_ram.master_we.next = master.wbm_ack_i and not write_back_enable

        # Slave bus
        slave_write_enable.next = slave.en_o and slave.we_o and tag_control.hit
        slave.ack_i.next = slave_rd_ack or slave_write_enable

    @always_seq(clock.posedge,reset)
    def proc_slave_rd_ack():
        if slave_rd_ack:
            slave_rd_ack.next = False
        elif tag_control.hit and slave.en_o and slave.we_o:
            slave_rd_ack.next = True


    return instances()
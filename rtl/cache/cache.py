"""
Bonfire Core Cache
(c) 2019,2020 The Bonfire Project
License: See LICENSE
"""
from myhdl import Signal,intbv,modbv,ConcatSignal,  \
                  block,always_comb,always_seq, always, instances, enum, now

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
        b4_pipelined=False,
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
    slave_adr_low = slave.adrLow  # int_log2(slave.xlen // 8) + slave.adrLow
    slave_adr_high = slave_adr_low + config.address_bits

    # local Signals
    write_back_enable = Signal(bool(0))
    cache_offset_counter = Signal(modbv(0)[config.cl_bits:]) 
    master_offset_counter = Signal(modbv(0)[config.cl_bits:])

    # Slave bus control
    slave_rd_ack = Signal(bool(0))
    slave_write_enable = Signal(bool(0))
    slave_stall =  Signal(bool(0))

    # Slave adress slice stripped from lower (not used...) bits
    slave_adr_slice = Signal(modbv(0)[config.address_bits:])
    slave_adr_reg =  Signal(modbv(0)[config.address_bits:])
    en_r = Signal(bool(0)) # Registered slave en signal

    @always_comb
    def proc_adr_slice():

        if en_r:
            slave_adr_slice.next = slave_adr_reg
        else:    
            slave_adr_slice.next = slave.adr_o[slave_adr_high:slave_adr_low]

    # Splitted slave adr
    slave_adr_splitted = cache_way.AddressBundle(config)
    s_adr_i = slave_adr_splitted.from_bit_vector(slave_adr_slice)

    

    wbm_enable = Signal(bool(0)) # Enable signal for master Wishbone bus

    # Cache RAM
    cache_ram = CacheRAMBundle(config)
    c_r_i = cache_ram_instance(cache_ram,clock)


    if config.num_ways == 1:
        tag_control = cache_way.CacheWayBundle(config)
        tc_i = cache_way.cache_way_instance(tag_control,clock,reset)

        @always_comb
        def comb():
            cache_ram.slave_adr.next = ConcatSignal(slave_adr_splitted.tag_index,slave_adr_splitted.word_index[config.cl_bits_slave:config.cl_bits])

            if write_back_enable:
                cache_ram.master_adr.next = ConcatSignal(tag_control.buffer_index,cache_offset_counter)
            else:
                cache_ram.master_adr.next = ConcatSignal(tag_control.tag_index,master_offset_counter)
    else:
        pass # TODO: Add support for num_ways > 1


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
             cache_ram.slave_db_wr.next =  slave.db_wr
             cache_ram.slave_we.next = slave.we_o
             slave.db_rd.next = cache_ram.slave_db_rd
    else:
        # Calcluate slave bus address bits for selecting the right 32 slice
        # from the master bus
        mx_low = 0
        mx_high = mx_low + int_log2(config.mux_size)
        # Debug only signals 
        slave_db_mux_debug = Signal(modbv(0)[int_log2(config.mux_size):])

        
        @always_comb
        def db_mux_n():
            # Data bus multiplexer
            slave_db_mux_debug.next = slave_adr_slice[mx_high :mx_low]
            for i in range(0,config.mux_size):
                # For writing the Slave bus can just be demutiplexed n times
                # Write Enable is done on byte lane level
                cache_ram.slave_db_wr[(i+1)*32:i*32].next = slave.db_wr

                if slave_adr_slice[mx_high :mx_low] == i:
                     # Write enable line multiplexer
                    cache_ram.slave_we[(i+1)*4:i*4].next = slave.we_o
                    # Databus Multiplexer, select the 32 Bit word from the cache ram word.
                    slave.db_rd.next = cache_ram.slave_db_rd[(i+1)*32:(i*32)]
                else:
                    cache_ram.slave_we[(i+1)*4:i*4].next = 0    


    @always_comb
    def proc_slave_write_enable():
         slave_write_enable.next = slave.en_o and slave.we_o and tag_control.hit

    @always_comb
    def cache_control_comb():

        

        # Tag Control

        tag_control.en.next = slave.en_o or en_r
        tag_control.we.next = (master.wbm_ack_i and wbm_state==t_wbm_state.wb_finish) or slave_write_enable
        tag_control.dirty.next = slave_write_enable
        tag_control.valid.next = not write_back_enable
        tag_control.adr.next = slave_adr_slice

        # Cache RAM control signals
        # Slave side
        cache_ram.slave_en.next = tag_control.hit and slave.en_o or en_r
        # Master side
        cache_ram.master_en.next = ( master.wbm_ack_i and wbm_enable ) or \
                                   ( write_back_enable and wbm_state == t_wbm_state.wb_idle )

        cache_ram.master_we.next = master.wbm_ack_i and not write_back_enable
        cache_ram.master_db_wr.next = master.wbm_db_i
       
        # Slave bus
        slave.ack_i.next = slave_rd_ack  or slave_write_enable
        slave.stall_i.next = slave_stall

        # Master bus
        master.wbm_cyc_o.next = wbm_enable
        master.wbm_stb_o.next = wbm_enable
        master.wbm_db_o.next = cache_ram.master_db_rd
                            

    @always(clock.posedge)
    def proc_reg_adr():
        if slave.en_o and not tag_control.hit and not slave_stall:
            slave_adr_reg.next = slave.adr_o[slave_adr_high:slave_adr_low]


    @always_seq(clock.posedge,reset)
    def proc_slave_control():

        if slave.en_o and not tag_control.hit:
            # Stall bus when no immediate hit on new bus cycle
            slave_stall.next = True
            en_r.next = True

        if slave_rd_ack:
            slave_rd_ack.next = False
        elif tag_control.hit and  ( slave.en_o or  en_r ) and not slave.we_o:
            slave_rd_ack.next = True
            slave_stall.next = False
            en_r.next = False


    @always_comb
    def proc_master_adr():
                   
        if write_back_enable:
            sig_temp = ConcatSignal(tag_control.tag_value,
                                    tag_control.buffer_index,master_offset_counter)
        else:
            sig_temp = ConcatSignal(slave_adr_splitted.tag_value,
                                    slave_adr_splitted.tag_index,
                                    master_offset_counter)   
        master.wbm_adr_o.next = sig_temp    


    # State engine for cache refill/writeback
    @always_seq(clock.posedge,reset)
    def master_rw():

        if wbm_state == t_wbm_state.wb_idle:
            if tag_control.miss and not tag_control.hit:
                wbm_enable.next = True
                for i in range(0,len(master.wbm_sel_o)):
                    master.wbm_sel_o.next[i] = True
                
                master.wbm_cti_o.next = 0b010    
                if write_back_enable:
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
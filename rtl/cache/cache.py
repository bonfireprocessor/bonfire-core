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

class BusInputBundle():
    def __init__(self,config,xlen=32):
        self.slave_en = Signal(bool(0))
        self.slave_adr_slice = Signal(modbv(0)[config.address_bits:]) # Slave adress slice stripped from lower (not used...) bits
        self.slave_we = Signal(modbv(0)[xlen//8:])
        self.slave_write = Signal(modbv(0)[xlen:])

class BusOutputBundle():
    def __init__(self,config,xlen=32):        
        self.slave_read =  Signal(modbv(0)[xlen:])
      

@block
def cache_dbslave_connect(db_slave,bus_input,bus_output,hit,clock,reset,config):

     # Constants
    slave_adr_low = db_slave.adrLow  
    slave_adr_high = slave_adr_low + config.address_bits

    slave_adr_reg =  Signal(modbv(0)[config.address_bits:])
    en_r = Signal(bool(0)) # Registered slave en signal
    slave_we_r = Signal(modbv(0)[len(db_slave.we_o):])
    slave_write_r = Signal(modbv(0)[db_slave.xlen:])
    slave_ack = Signal(bool(0))

    @always_comb
    def proc_input_comb():

        bus_input.slave_en.next = en_r and db_slave.en_o
        db_slave.stall_i.next = en_r and db_slave.en_o

        if en_r:
            bus_input.slave_adr_slice.next = slave_adr_reg
            bus_input.slave_we.next = slave_we_r
            bus_input.slave_write.next = slave_write_r
        else:
            bus_input.slave_adr_slice.next = db_slave.adr_o[slave_adr_high:slave_adr_low]
            bus_input.slave_we.next = db_slave.we_o
            bus_input.slave_write.next = db_slave.db_wr

    @always_comb
    def proc_output_comb():

        db_slave.ack_i.next = slave_ack
        db_slave.db_rd = bus_output.slave_read


    # Registers that do not need to be reset
    @always(clock.posedge)
    def proc_reg_slave():
        if db_slave.en_o and not ( en_r or hit ):
            slave_adr_reg.next = db_slave.adr_o[slave_adr_high:slave_adr_low]
            slave_we_r.next = db_slave.we_o
            slave_write_r.next = db_slave.db_wr        

    @always_seq(clock.posedge,reset)
    def proc_slave_control():

        if db_slave.en_o and not ( en_r or hit ):            
            en_r.next = True
            

        if hit and  ( db_slave.en_o or  en_r ):
            slave_ack.next = True
            en_r.next = False
        else:
           slave_ack.next = False

    return instances()


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

        @always(clock.posedge)
        def db_mux_sync():
            if tag_control.hit and  ( db_slave.en_o or  en_r ):
                slave_db_mux_reg.next = bus_input.slave_adr_slice[mx_high :mx_low]


        @always_comb
        def db_mux_n():
            # Data bus multiplexer
            for i in range(0,config.mux_size):
                if slave_db_mux_reg == i:
                    # Databus Multiplexer, select the 32 Bit word from the cache ram word.
                    bus_output.slave_read.next = cache_ram.slave_db_rd[(i+1)*32:(i*32)]
            
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
            cache_ram.slave_adr.next = concat(slave_adr_splitted.tag_index,slave_adr_splitted.word_index[config.cl_bits_slave:config.cl_bits])

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
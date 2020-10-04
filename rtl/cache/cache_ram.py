"""
Bonfire Core Cache 
(c) 2019,2020 The Bonfire Project
License: See LICENSE
"""
from __future__ import print_function

from rtl.util import int_log2
from myhdl import Signal,modbv, intbv, \
                  block,always,instances, now

class CacheRAMBundle:
    def __init__(self,config):
        c = config
        self.config = c
        # Slave Interface
        self.slave_en = Signal(bool(0))
        self.slave_adr = Signal(modbv(0)[int_log2(c.cache_size_m_words):])
        self.slave_db_rd = Signal(modbv(0)[c.master_data_width:])
        self.slave_db_wr = Signal(modbv(0)[c.master_data_width:])
        self.slave_we = Signal(modbv(0)[c.master_width_bytes:])
        # Master Interface
        self.master_en = Signal(bool(0))
        self.master_adr =  Signal(modbv(0)[int_log2(c.cache_size_m_words):])
        self.master_db_rd = Signal(modbv(0)[c.master_data_width:])
        self.master_db_wr = Signal(modbv(0)[c.master_data_width:])
        self.master_we = Signal(bool(0))



@block
def cache_ram_instance(bundle,clock,simulation_checks=False):
    """
    bundle : Cache RAM bundle
    """
    c = bundle.config

    cache_ram =  [Signal(modbv(0)[c.master_data_width:]) for ii in range(0, c.cache_size_m_words)]

    if simulation_checks:
        @alway(clock.posedge)
        def sim_checks():
            # Write collision check, only relevant in simulation
            if bundle.slave_en and bundle.master_en and \
               bundle.slave_we and bundle.master_we and \
               bundle.slave_adr == bundle.master_adr:

               print("@{}: write collision to cache ram for adr:{}".format(now(),bundle.slave_adr))



    @always(clock.posedge)
    def seq_slave():

        if bundle.slave_en:
            for b in range(0,c.master_width_bytes):
                if bundle.slave_we[b]:
                    cache_ram[bundle.slave_adr].next[(b+1)*8:b*8] = bundle.slave_db_wr[(b+1)*8:b*8]

        #TODO: Check why an addtional mux/FF is generated when reading is gated by slave_en.  
        bundle.slave_db_rd.next = cache_ram[bundle.slave_adr]

    @always(clock.posedge)
    def seq_master():
        
        if bundle.master_en:
            if bundle.master_we:
                cache_ram[bundle.master_adr].next = bundle.master_db_wr
            bundle.master_db_rd.next = cache_ram[bundle.master_adr]  

    return instances()


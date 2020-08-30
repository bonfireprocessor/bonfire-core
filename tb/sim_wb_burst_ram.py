"""
Bonfire Core simulation ram 
(c) 2019,2020 The Bonfire Project
License: See LICENSE
"""
from __future__ import print_function

from myhdl import Signal,modbv,block,always, always_comb, enum, concat, instances, now

@block
def ram_interface(ram,wb_bus, pattern_mode, clock, config):
    """
        Instantiate a RAM interface  for simulation

        ram : RAM Array, should be [Signal(modbv(0)[xlen:]) for ii in range(0, ram_size)]
        wb_bus: Wishbone bus (class CacheMasterWishboneBundle)
        pattern_mode : if True, insted of RAM content an address dependant pattern is read
        clock, reset : Clock and reset
        config : CacheConfig
    """

    t_mstate = enum('m_idle','m_burst')
    m_state = Signal(t_mstate.m_idle)

    def get_pattern(adr):

        bitpos = 0
        word_adr = modbv(0)[wb_bus.adrLow:]
        d = modbv(0)[config.master_data_width:]
        for i in range(0,config.master_data_width//32):
            d[bitpos+32:bitpos] = concat(adr,word_adr)
            bitpos += 32
            word_adr += 4

        return d    


    
    @always_comb
    def mem_read():
        if wb_bus.wbm_stb_o and not wb_bus.wbm_we_o:
            if pattern_mode:
                wb_bus.wbm_db_i.next = get_pattern(wb_bus.wbm_adr_o)
            else:
                assert wb_bus.wbm_adr_o < len(ram), "Out of bound RAM access to address {}".format(wb_bus.wbm_adr_o)
                wb_bus.wbm_db_i.next = ram[wb_bus.wbm_adr_o]


    @always(clock.posedge)
    def mem_simul():
        if wb_bus.wbm_cyc_o and wb_bus.wbm_stb_o and wb_bus.wbm_we_o:
            for i in range(0,len(wb.wbm_sel_o)):
                if wb.wbm_sel_o[i]:
                    ram[wb.wbm_adr_o].next[(i+1)*8:i*8] = wb.wbm_db_o[(i+1)*8:i*8]

        if m_state == t_mstate.m_idle:
            if wb_bus.wbm_cyc_o and wb_bus.wbm_stb_o:
                m_state.next = t_mstate.m_burst
                wb_bus.wbm_ack_i.next = True
        else:
            if wb_bus.wbm_cti_o == 0b000 or   wb_bus.wbm_cti_o == 0b111:
                  wb_bus.wbm_ack_i.next =  False
                  m_state.next = t_mstate.m_idle

    return instances()


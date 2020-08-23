"""
Bonfire Core Cache tag RAM 
(c) 2019,2020 The Bonfire Project
License: See LICENSE
"""

from __future__ import print_function

from myhdl import Signal,modbv,block,always, instances, now 

#from rtl.cache.cache_way import TagDataBundle


@block
def tag_ram_instance(data_in,data_out,we,adr,clock,reset,config):
    """
    data_in: TagDataBundle
    data_out: TagDataBundle
    we: Write enable signal
    adr: RAM address to read/write from/to
    clock, reset
    config: CacheConfig
    """

    width = data_in.get_len()

    ram_array = [Signal(modbv(0)[width:]) for ii in range(0, config.tag_ram_size)]

    tagdata_in = Signal(modbv(0)[width:])
    tagdata_out = Signal(modbv(0)[width:])

    tagdi_instance = data_in.to_bit_vector(tagdata_in)
    tagdo_instance = data_out.from_bit_vector(tagdata_out)

    @always(clock.posedge)
    def ram_seq():
       
        if reset: # explicit reset handling here
            tagdata_out.next = 0
        if we:
            ram_array[adr].next = tagdata_in
            tagdata_out.next = tagdata_in # write first ram
        else:
            tagdata_out.next = ram_array[adr]

    return instances()
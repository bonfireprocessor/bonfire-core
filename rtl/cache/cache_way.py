"""
Bonfire Core Cache 
(c) 2019,2020 The Bonfire Project
License: See LICENSE
"""

from myhdl import Signal,intbv,modbv,ConcatSignal, \
                  block,always_comb,always_seq,instances, now

class CacheWayBundle:
    def __init__(self,cache_config):
        #Config
        self.config = cache_config
        self.tag_adr_len = cache_config.cache_adr_bits-cache_config.cl_bits

      
        
        # Input Signals for read/write to tag RAM
        # Control
        self.en = Signal(bool(0))
        self.we = Signal(bool(0)) # Tag RAM write enable
        # Data
        self.dirty = Signal(bool(0))
        self.valid = Signal(bool(0))
        self.adr = Signal(modbv(0)[cache_config.address_bits:])

        # Output Signals
        
        self.tag_index = Signal(modbv(0)[tag_adr_len:])
        self.buffer_index = Signal(modbv(0)[tag_adr_len:])

        self.hit = Signal(bool(0))
        self.miss = Signal(bool(0))
        self.dirty_miss = Signal(bool(0))
        self.tag_valid = Signal(bool(0))
        self.tag_value = Signal(modbv(0)[cache_config.tag_ram_bits:])


class TagDataBundle:
    def __init__(self,tag_value_len):
        self.tag_value_len=tag_value_len
        self.valid = Signal(bool(0))
        self.dirty = Signal(bool(0))
        self.address = Signal(modbv(0)[tag_value_len:])

    def get_len(self):
        # return with of Bundle in bits
        return self.tag_value_len + 2

    @block
    def to_bit_vector(self,tagdata):

        @always_comb
        def comb():
            t_len = self.tag_value_len + 2
            #tagdata.next=ConcatSignal(self.valid,self.dirty,self.address)
            tagdata.next[t_len-1] = self.valid
            tagdata.next[t_len-2] = self.dirty
            tagdata.next[t_len-2:] = self.address

        return instances()

    @block
    def from_bit_vector(self,tagdata):

        @always_comb
        def comb():
            t_len = self.tag_value_len + 2
            self.valid.next = tagdata[t_len-1]
            self.dirty.next = tagdata[t_len-2]
            self.address.next = tagdata[t_len-2:]

        return instances()    


# @block
# def cache_way_instance(bundle,clock,reset):

    
#     c = bundle.config
    


   



#     @always_comb
#     def comb():
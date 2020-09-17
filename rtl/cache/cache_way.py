"""
Bonfire Core Cache 
(c) 2019,2020 The Bonfire Project
License: See LICENSE
"""

from myhdl import Signal,intbv,modbv,ConcatSignal, \
                  block,always_comb,always_seq,instances, now

from  rtl.cache.tag_ram   import tag_ram_instance              

class CacheWayBundle:
    def __init__(self,cache_config):
        #Config
        self.config = cache_config
        tag_adr_len = cache_config.line_select_adr_bits

      
        
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
        
        assert len(self.address) == self.tag_value_len
        t_len = self.tag_value_len + 2

        @always_comb
        def comb():
           
            tagdata.next[t_len-1] = self.valid
            tagdata.next[t_len-2] = self.dirty
            tagdata.next[t_len-2:] = self.address

        return instances()

    @block
    def from_bit_vector(self,tagdata):

        assert len(self.address) == self.tag_value_len
        t_len = self.tag_value_len + 2

        @always_comb
        def comb():
           
            self.valid.next = tagdata[t_len-1]
            self.dirty.next = tagdata[t_len-2]
            self.address.next = tagdata[t_len-2:]

        return instances()    


class AddressBundle:
    def __init__(self,config):
        self.config = config
        c = config 
        self.tag_value = Signal(modbv(0)[c.tag_ram_bits:])
        self.tag_index = Signal(modbv(0)[c.line_select_adr_bits:])
        self.word_index = Signal(modbv(0)[c.cl_bits_slave:])

    @block
    def  from_bit_vector(self,adr):
        c = self.config

        @always_comb
        def comb():
           
            self.tag_value.next = adr[c.address_bits:c.tag_value_adr_bit_low]
            self.tag_index.next =  adr[c.tag_value_adr_bit_low:c.cl_bits_slave]
            self.word_index.next = adr[c.cl_bits_slave:]

        return instances()

    def debug_print(self):
        print("AddressBundle content: value: {}  index: {} word_index: {}".format(self.tag_value,
                                                                                  self.tag_index,
                                                                                  self.word_index))


@block
def cache_way_instance(bundle,clock,reset):

    
    c = bundle.config

    tag_index = Signal(modbv(0)[c.line_select_adr_bits:]) # Tag index to be read
    tag_in = TagDataBundle(c.tag_ram_bits)
    tag_buffer = TagDataBundle(c.tag_ram_bits) # Last read Tag RAM item
    buffer_index = Signal(modbv(0)[c.line_select_adr_bits:])  # Index of last read Tag RAM item

    slave_adr_splitted = AddressBundle(c)
    s_adr_i = slave_adr_splitted.from_bit_vector(bundle.adr)

    t_i = tag_ram_instance(tag_in,tag_buffer,bundle.we,tag_index,clock,reset,c)
    

    @always_comb
    def assign():
        # TODO: Check correctness of indicies
        tag_index.next =  slave_adr_splitted.tag_index
        tag_in.address.next = slave_adr_splitted.tag_value
        tag_in.valid.next = bundle.valid
        tag_in.dirty.next = bundle.dirty

    @always_comb
    def hit_miss():
        # Check hit/miss
        index_match = buffer_index == tag_index
        tag_match = tag_buffer.valid and tag_buffer.address == tag_in.address

        bundle.hit.next = index_match and tag_match and bundle.en
        if bundle.en and index_match and not tag_match:
            bundle.miss.next = True
            bundle.dirty_miss.next = tag_buffer.dirty
        else:
            bundle.miss.next = False
            bundle.dirty_miss.next = False

        # Tag Output
        bundle.tag_valid.next = tag_buffer.valid
        bundle.tag_value.next = tag_buffer.address
        bundle.buffer_index.next = buffer_index
        bundle.tag_index.next = tag_index

    @always_seq(clock.posedge,reset)
    def seq():
        buffer_index.next = tag_index

    return instances()    
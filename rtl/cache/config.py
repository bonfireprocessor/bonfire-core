"""
Bonfire Core cache config parameters
(c) 2019,2020 The Bonfire Project
License: See LICENSE
"""

from __future__ import print_function
from myhdl import modbv
from rtl.util import int_log2




class CacheConfig:
    def __init__(self,
                 master_data_width = 128,
                 line_size = 4, # Line size in MASTER_DATA_WIDTH  words
                 cache_size_m_words = 2048, # Cache Size in MASTER_DATA_WIDTH Bit words
                 address_bits = 30, #  Number of bits of chacheable address range
                 num_ways = 1 # Number of cache ways 
                 ): 
    
    
        assert master_data_width == 32 or \
               master_data_width == 64 or  \
               master_data_width == 128 or \
               master_data_width == 256, \
               "CacheConfig: master_data_width must be 32, 64, 128 or 256"

        self.master_data_width = master_data_width
        self.master_width_bytes =  master_data_width // 8  
        self.mux_size = master_data_width // 32  # Multiplex factor from memory bus to CPU bus (CPU bus is always 32 Bits)
        self.word_select_bits = int_log2(self.mux_size)

        self.line_size = line_size 
        self.cl_bits = int_log2(line_size) # Bits for adressing a master word in a cache line
        self.cl_bits_slave = self.cl_bits + int_log2(self.mux_size) # Bits for addressing a 32 Bit word in a cache line  
        self.cache_size_m_words = cache_size_m_words
        self.cache_size_bytes = cache_size_m_words * self.master_width_bytes

        self.way_adr_bits = int_log2(num_ways) # number of bits to select a way
        self.num_ways = num_ways
        self.set_adr_bits = int_log2(cache_size_m_words) - self.way_adr_bits # adress bits for a set in cache RAM
        self.line_select_adr_bits = self.set_adr_bits - self.cl_bits # adr bits for selecting a cache line
        self.tag_ram_size = 2**self.line_select_adr_bits # the Tag RAM size is defined by the size of line select address
        self.tag_ram_bits = address_bits - self.line_select_adr_bits - self.cl_bits - self.word_select_bits
 
        self.address_bits = address_bits # Number of bits of chacheable address range
        self.tag_value_adr_bit_low = self.address_bits - self.tag_ram_bits # Lowest bit of tag value part of cachable address

        line_size_slave=2**self.cl_bits_slave
        assert line_size_slave == line_size * self.mux_size, "line size does not match bus mux factor"
      
    # Simulation only methods, cannot be converted  
    def create_address(self,value_part,line_part,word_select_part):
        adr = modbv(0)[self.address_bits:]
        adr[self.address_bits:self.tag_value_adr_bit_low]=value_part
        adr[self.tag_value_adr_bit_low:self.cl_bits_slave]=line_part
        adr[self.cl_bits_slave:]=word_select_part
        return adr 

    def print_address(self,adr):
        print("Adr:{}".format(adr))
        v_low = self.tag_value_adr_bit_low 
        value_part= adr[ self.address_bits:v_low]
        assert len(value_part)==self.tag_ram_bits
        print("Tag Value part from bit {} to {} ({} bits) : {}:({})".format(self.address_bits-1,
                v_low, len(value_part), bin(value_part), value_part))      
        line_part =  adr[v_low:self.cl_bits_slave]
        assert len(line_part)==self.line_select_adr_bits
        print("Cache line (tag index) part from bit {} to {} ({} bits) : {}:({})".format(v_low-1,self.cl_bits_slave, 
              len(line_part),  bin(line_part), line_part))
        wp =  adr[self.cl_bits_slave:]
        print("word select part from bit {} to {} ({} bits) : {}:({})".format(self.cl_bits_slave-1,0, len(wp), bin(wp), wp))

       
    def print_config(self):
        print(self.__dict__)
        template= """
        Cache size: {cache_size_m_words} * {master_data_width} bits ( {cache_size_bytes} Bytes )
        Cache size in bytes: {cache_size_bytes}
        Line size: {line_size} * {master_data_width} bits or {line_size_slave} * 32 Bits
        Number of ways: {num_ways}
        
        Tag ram size: {tag_ram_size} * {tag_ram_bits} bits (without control bits)
        Tag ram address length: {line_select_adr_bits} bits
        Cacheable adress range {address_bits} bits
        Cache organization: 
        {tag_ram_size} sets * {num_ways} ways * {set_bytes} Bytes"""
        
        print(template.format(set_bytes=self.line_size * self.master_width_bytes,
                              line_size_slave=2**self.cl_bits_slave,
                              **self.__dict__))


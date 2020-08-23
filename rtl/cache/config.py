"""
Bonfire Core cache config parameters
(c) 2019,2020 The Bonfire Project
License: See LICENSE
"""

from __future__ import print_function
from math import log2

def int_log2(v):
    l = log2(v)
    assert int(l)==l, "{} must be power of 2".format(v)
    return int(l)



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
        self.cl_bits = int_log2(line_size) # Bits for adressing a word in a cache line
        self.cache_size_m_words = cache_size_m_words
        self.cache_size_bytes = cache_size_m_words * self.master_width_bytes

        self.way_adr_bits = int_log2(num_ways) # number of bits to select a way
        self.num_ways = num_ways
        self.set_adr_bits = int_log2(cache_size_m_words) - self.way_adr_bits # adress bits for a set in cache RAM
        self.line_select_adr_bits = self.set_adr_bits - self.cl_bits # adr bits for selecting a cache line
        self.tag_ram_size = 2**self.line_select_adr_bits # the Tag RAM size is defined by the size of line select address
        self.tag_ram_bits = address_bits -self.line_select_adr_bits - self.cl_bits - self.word_select_bits
 
        self.address_bits = address_bits # Number of bits of chacheable address range
      

       
    def print_config(self):
        print(self.__dict__)
        template= """
        Cache size: {cache_size_m_words} * {master_data_width} bits ( {cache_size_bytes} Bytes )
        Cache size in bytes: {cache_size_bytes}
        Line size: {line_size} * {master_width_bytes} Bytes
        Number of ways: {num_ways}
        
        Tag ram size: {tag_ram_size} * {tag_ram_bits} bits (without control bits)
        Tag ram address length: {line_select_adr_bits} bits
        Cacheable adress range {address_bits} bits
        Cache organization: 
        {tag_ram_size} sets * {num_ways} ways * {set_bytes} Bytes"""
        
        print(template.format(set_bytes=self.line_size * self.master_width_bytes,**self.__dict__))


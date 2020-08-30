"""
MyHDL utility functions
(c) 2019 The Bonfire Project
License: See LICENSE
"""

from myhdl import intbv
from math import log2

def signed_resize(v,size):
    result = intbv(0)[size:]
    
    result[len(v):]=v
    sign = v[len(v)-1]
    for i in range(len(v),size):
        result[i] =sign 
    
    return result    

def int_log2(v):
    l = log2(v)
    assert int(l)==l, "{} must be power of 2".format(v)
    return int(l)
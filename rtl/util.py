"""
MyHDL utility functions
(c) 2019 The Bonfire Project
License: See LICENSE
"""

from myhdl import intbv

def signed_resize(v,size):
    result = intbv(0)[size:]
    
    result[len(v):]=v
    sign = v[len(v)-1]
    for i in range(len(v),size):
        result[i] =sign 
    
    return result    

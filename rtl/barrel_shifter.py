"""
Barrel Shifter Library
(c) 2019 The Bonfire Project
License: See LICENSE
"""

from myhdl import *



@block
def left_shift_comb(d_i,d_o, shift_i, fill_i,c_sh_power_high=5,c_sh_power_low=0):
    """
  Parameters:
    Runtime:

        d_i     : input Signal bit vector Input Data (aribitrary length)
        d_o     : output Signal bit vector : Shiftet output, must be same length as d_i
        shift_i : bit vector, shift amount
        fill_i :  bool fill value, which is filled in from right side

    Configuration:
        c_sh_power_high : Highest bit of shift_i power of two, in python style, exluding high value
        c_sh_power_low  : Lowest bit of shift_i power of two

    Realizes a combinatorical barrel shifter. The c_sh_power_high and c_sh_power_low define the power of two values
    for the shift amount. This allows creation of cascaded barrel shifters, e.g. with pipeline stages in between.
    For example the first instance will shift the powers 0..2, the second one 3..4
    """

    l=len(d_i)
    
    @always_comb
    def comb():
        p=c_sh_power_low
       

        temp=modbv(d_i.val)[l:]
        
        fill=intbv(0)[l:]
        for i in range(len(fill)):   
            fill[i]=fill_i 

        for i in range(c_sh_power_high-c_sh_power_low):
            shift= 2**p
            if  shift_i[i]==1:
                #print l-shift, shift 

                #print(bin(fill[2**p:]))
                temp[32:] = concat(temp[l-shift:0],fill[2**p:])
            p+=1

        d_o.next=temp

    return instances()

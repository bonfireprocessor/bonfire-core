"""
Bonfire Core simulation monitor
(c) 2019,2020 The Bonfire Project
License: See LICENSE
"""
from __future__ import print_function

from myhdl import *


@block
def monitor_instance(bus,clock,base_adr=0x10000000,registered_ack=False):

    @always(clock.posedge)
    def monitor_proc():

        if registered_ack and bus.ack_i:
            bus.ack_i.next = False 

        if bus.en_o:
            if bus.we_o:   
                print("Monitor write: @{} {}: {} ({})".format(now(),bus.adr_o,bus.db_wr,int(bus.db_wr.signed())))
                if bus.adr_o==base_adr:
                    raise StopSimulation
            if registered_ack:    
                bus.ack_i.next = True         
    
    
    if not registered_ack:
        @always_comb
        def ack():
            bus.ack_i.next = bus.en_o

    return instances()

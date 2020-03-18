"""
Wishbone Bus functional module, test bench
(c) 2019,2020 The Bonfire Project
License: See LICENSE
"""

from __future__ import print_function
import random

from myhdl import *
from rtl.bonfire_interfaces import Wishbone_master_bundle



class Wishbone_bfm:
    def __init__(self):
        pass



    @block
    def Wishbone_check(self,wb,clock,reset):

        assert not wb.pipelined, "Wishbone_check, pipelined mode not yet supported"

        active_cycle = Signal(bool(0)) # Active Wishbone cycle (cyc_o and stb_o asserted)
        active_cycle_r = Signal(bool(0)) # registered, stays true until ack is asserted and cycle terminated
        check_term = Signal(bool(0)) # Asserted when cycle terminates, will trigger after cycle check code - see below

        wait_counter = Signal(0)


        @always_comb
        def comb():
            active_cycle.next = wb.wbm_cyc_o and wb.wbm_stb_o

        @always_seq(clock.posedge,reset=reset)
        def cycle_term():

            if wb.wbm_ack_i:
                wb.wbm_ack_i.next = False
            else:
                if active_cycle and not active_cycle_r: # begin of new bus cycle
                    w = random.randint(0,2)
                    if w>0:
                        wait_counter.next = w
                        active_cycle_r.next = True
                    else:
                        wb.wbm_ack_i.next = True     

                if active_cycle_r: # Subsequent clock cylces of bus cycle
                    if wait_counter==0:
                        active_cycle_r.next = False
                        wb.wbm_ack_i.next = True
                        if not wb.wbm_we_o:
                            wb.wbm_db_i.next = 0xdeadbeef
                    else:
                        wait_counter.next = wait_counter - 1


        @always_seq(clock.posedge,reset=reset)
        def wb_observe():
            
            if active_cycle and wb.wbm_ack_i:
                
                check_term.next = True 
                print("@{}: wb cyc. trm. Adr:{} we: {}, sel: {}".format(now(),hex(wb.wbm_adr_o<<2),wb.wbm_we_o,bin(wb.wbm_sel_o)))
                if wb.wbm_we_o:
                    print("write data: {}".format(hex(wb.wbm_db_o)))
                else:
                    print("read data: {}".format(hex(wb.wbm_db_i))) 

            if active_cycle_r:
                assert active_cycle,"wbm_cyc_o or wbm_stb_o deasserted without ack"
            
            if check_term:
                assert not wb.wbm_stb_o,"wbm_stb_o not deasserted after ack"
                assert not wb.wbm_we_o,"wbm_we_o not deasserted after ack"
                check_term.next=False

        return instances()    

            
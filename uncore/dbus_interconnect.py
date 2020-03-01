"""
Bonfire interconnect for dbus_bundle
(c) 2019,2020 The Bonfire Project
License: See LICENSE
"""

from __future__ import print_function
from myhdl import *

class AdrMask:
    def __init__(self,upper,lower,value):
        self.upper = upper
        self.lower = lower
        self.mask = value



class DbusInterConnects:

    @staticmethod
    @block
    def Master3Slaves(master,slave1,slave2,slave3,clock,reset, adrmask1, adrmask2,adrmask3):

        s_en = Signal(modbv(0)[3:])
        s_en_r = Signal(modbv(0)[3:])
        mux_sel = Signal(modbv(0)[3:])
       
        busy = Signal(bool(0)) # Interconnect busy with an active bus cycle
        ack = Signal(bool(0))

        @always_seq(clock.posedge,reset=reset)
        def seq():

            if busy and ack:
                busy.next = False
            else:
                s_en_r.next = s_en
                b = False
                for i in range(len(s_en)):
                    b = b or s_en[i]

                busy.next = b and not ack

        @always_comb
        def mux_sel_proc():
            for i in range(len(s_en)):
                mux_sel.next[i] = s_en[i] or ( s_en_r[i] and busy ) 

        @always_comb
        def adrsel():
            s_en.next[0] = master.adr_o[adrmask1.upper:adrmask1.lower] == adrmask1.mask and master.en_o 
            s_en.next[1] = master.adr_o[adrmask2.upper:adrmask2.lower] == adrmask2.mask and master.en_o 
            s_en.next[2] = master.adr_o[adrmask3.upper:adrmask3.lower] == adrmask3.mask and master.en_o 

        # @always(clock.posedge)
        # def mon():
        #     if s_en:
        #         print("adr:{} s_en:{}".format(master.adr_o,bin(s_en,3)))    

        @always_comb
        def comb():
            slave1.en_o.next = s_en[0]
            slave2.en_o.next = s_en[1]
            slave3.en_o.next = s_en[2]
            slave1.adr_o.next = master.adr_o
            slave2.adr_o.next = master.adr_o
            slave3.adr_o.next = master.adr_o
            slave1.db_wr.next = master.db_wr
            slave2.db_wr.next = master.db_wr
            slave3.db_wr.next = master.db_wr
            slave1.we_o.next = master.we_o
            slave2.we_o.next = master.we_o
            slave3.we_o.next = master.we_o

            # Stall master when the seleted slave changes.
            # This is needed because the interconnet has no mechanism to queue bus cycles
            stall = busy and master.en_o and s_en != s_en_r

            t_ack = False

            master.error_i.next = False 
            if mux_sel[0]:
                stall = stall or  slave1.stall_i
                t_ack = slave1.ack_i.val
                master.db_rd.next = slave1.db_rd
            elif mux_sel[1]:
                stall = stall or slave2.stall_i
                t_ack = slave2.ack_i.val
                master.db_rd.next = slave2.db_rd
                master.error_i.next = False
            elif mux_sel[2]:
                stall = stall or slave3.stall_i
                t_ack = slave3.ack_i.val
                master.db_rd.next = slave3.db_rd   
            else:
                master.error_i.next = master.en_o
                
                
            master.ack_i.next = t_ack
            ack.next = t_ack                
            master.stall_i.next = stall    
            

        return instances()


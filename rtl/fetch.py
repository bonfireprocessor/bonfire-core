"""
RISC-V insturction fetch module
(c) 2019 The Bonfire Project
License: See LICENSE
"""
from __future__ import print_function

from myhdl import *


class FetchUnit:
    def __init__(self,config):
        self.config = config
        xlen = config.xlen
        self.reset_address=config.reset_address

        self.stall_i = Signal(bool(0)) # Stall input from next stage

        # # Jump control
        self.jump_i =  Signal(bool(0)) 
        self.jump_dest_i = Signal(modbv(0)[xlen:])

        # # Output
        # self.valid_o = Signal(bool(0)) # Output valid
        
        # self.current_ip_o = Signal(modbv(0)[xlen:]) # ip (PC) of current instruction
        # self.next_ip_o = Signal(modbv(0)[xlen:]) # ip (PC) of next instruction
        # self.word_o = Signal(modbv(0)[32:]) # actual instruction to decode


    @block
    def SimpleFetchUnit(self,fetch,backend,ibus,clock,reset):
        """
       
        fetch : FetchInputBundle, input to backend pipeline
        backend: control outputs of backend
        ibus : DBusBundle, instruction fetch bus

        clock: clock
        reset: reset 
        """
        ip = Signal(intbv(self.reset_address)[self.config.xlen:]) # Insruction pointer
        busy = Signal(bool(0)) # Start with busy asserted 
        current_word = Signal(modbv(0)[32:0])
        current_ip =  Signal(modbv(0)[self.config.xlen:0])
        valid = Signal(bool(0))

        run = Signal(bool(0))


        @always_comb
        def comb():
            ibus.en_o.next = not busy and run 
            ibus.adr_o.next = ip
            ibus.we_o = 0

            fetch.en_i.next = valid
            fetch.word_i.next = current_word
            fetch.next_ip_i.next = ip
           

        @always_seq(clock.posedge,reset=reset)
        def fetch_proc():

            if not run:
                run.next = True # Comming out of reset 
            else: 
                if not ( ibus.stall_i or busy or self.stall_i ):
                    current_ip.next = ip  
                    if self.jump_i:
                        ip.next = self.jump_dest_i
                    else:
                        ip.next = ip + 4

                if ibus.ack_i:
                    current_word.next = ibus.db_rd
                    fetch.current_ip_i.next = current_ip
                    valid.next = True
                    busy.next = False 
                else:
                    valid.next=False     


        return instances()

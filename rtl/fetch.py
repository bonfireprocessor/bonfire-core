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
    def SimpleFetchUnit(self,fetch,ibus,clock,reset):
        """
       
        fetch : FetchInputBundle, input to backend pipeline
        backend: control outputs of backend
        ibus : DBusBundle, instruction fetch bus

        clock: clock
        reset: reset 
        """
        ip = Signal(intbv(self.reset_address)[self.config.xlen:]) # Insruction pointer
        busy = Signal(bool(0)) # Start with busy asserted 
        valid = Signal(bool(0))
        jump_taken = Signal(bool(0))

        run = Signal(bool(0)) # processor not in reset 

        # Fifo 
        current_word = [Signal(modbv(0)[32:0]) for i in range(0,2)]
        current_ip =   [Signal(modbv(0)[self.config.xlen:0]) for i in range(0,3)]
        


        @always_comb
        def comb():
            ibus.en_o.next = not busy and run and not self.stall_i \
                             and not (self.jump_i and not jump_taken) # Supress en on new incomming jumps
            ibus.adr_o.next = ip
            ibus.we_o.next = 0

            fetch.en_i.next = valid 
            fetch.word_i.next = current_word[0]
            fetch.next_ip_i.next = current_ip[0] + 4 # TODO: look for better solution...
            fetch.current_ip_i.next = current_ip[0]
           

       
        @always_seq(clock.posedge,reset=reset)
        def fetch_proc():

            if not run:
                run.next = True # Comming out of reset 
            else: 
                if not self.jump_i:
                    jump_taken.next = False

                if  not ( ibus.stall_i or busy or self.stall_i ):
                    current_ip[2].next = ip  
                    if self.jump_i and not jump_taken:
                        ip.next = self.jump_dest_i
                        jump_taken.next = True
                    else:
                        ip.next = ip + 4

                if self.stall_i:
                    # Store pending fetch when next stage is stalled and block ourself
                    if ibus.ack_i:
                        current_word[1].next = ibus.db_rd
                        current_ip[1].next = current_ip[2]
                        busy.next = True
                        valid.next = True
                else:
                    if busy:
                        assert not ibus.ack_i, "Fetch: ack_i while busy asserted"
                        current_word[0].next = current_word[1]
                        current_ip[0].next = current_ip[1]
                        valid.next = True
                        busy.next = False
                    else:
                        if ibus.ack_i:
                            current_word[0].next = ibus.db_rd
                            current_ip[0].next = current_ip[2]
                            valid.next = True
                        else:    
                            valid.next = False 

                       

        return instances()

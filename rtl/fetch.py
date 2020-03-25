"""
RISC-V insturction fetch module
(c) 2019 The Bonfire Project
License: See LICENSE
"""
from __future__ import print_function

from myhdl import *
from pipeline_control import *


class InstructionBuffer(PipelineControl):
    def __init__(self,config):
        self.config = config

        PipelineControl.__init__(self)


    @block
    def bufferInstance(self,fetch_in,fetch_out,clock,reset):

        full = Signal(bool(0))
        busy = Signal(bool(0))
        word = Signal(modbv(0)[32:])
        current_ip = Signal(modbv(0)[self.xlen:])
        next_ip = Signal(modbv(0)[self.xlen:])

        p_inst = self.pipeline_instance(busy,full)    

        
        @always_seq(clock.posedge,reset=reset)
        def seq():

            if not busy and self.en_i:
                full.next = True
                word.next = fetch_in.word_i
                current_ip.next = fetch_in.current_ip_i
                next_ip.next = fetch_in.next_ip_i

            if full:
                if self.stall_i:
                    busy.next = True
                else:        
                    full.next = False

        @always_comb
        def comb():
            fetch_out.en_i.next = self.valid_o
            fetch_out.word_i.next = word
            fetch_out.current_ip_i.next = current_ip
            fetch_out.next_ip_i.next = next_ip

        return instances()


class FetchUnit(PipelineControl):

    def __init__(self,config):
        self.config = config
        xlen = config.xlen
        self.reset_address=intbv(config.reset_address)[xlen:]

        # # Jump control
        self.jump_i =  Signal(bool(0)) 
        self.jump_dest_i = Signal(modbv(0)[xlen:])

        PipelineControl.__init__(self,firstStage=True)

        

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
        busy = Signal(bool(0)) 
        valid = Signal(bool(0))

        jump_taken = Signal(bool(0))
        new_jump = Signal(bool(0))

        run = Signal(bool(0)) # processor not in reset 

        # Fifo 
        current_word = [Signal(modbv(0)[32:0]) for i in range(0,2)]
        current_ip =   [Signal(modbv(0)[self.config.xlen:0]) for i in range(0,3)]
        
        en = Signal(bool(0))
        outstanding = Signal(bool(0))

        p_inst = self.pipeline_instance(busy,valid)

        @always_comb
        def new_j():
            new_jump.next = self.jump_i and not jump_taken
             

        @always_comb
        def comb():
            e =  not busy and run and not self.stall_i \
                 and not new_jump # Supress ibus.en_o on new incomming jumps
            en.next = e
           
            ibus.en_o.next = e
            ibus.adr_o.next = ip
            #ibus.we_o.next = 0

            fetch.en_i.next = valid 
            fetch.word_i.next = current_word[0]
            fetch.next_ip_i.next = current_ip[0] + 4 # TODO: look for better solution...
            fetch.current_ip_i.next = current_ip[0]
           

       
        @always_seq(clock.posedge,reset=reset)
        def fetch_proc():

            if en and not ibus.ack_i:
                outstanding.next = True
            elif not en and ibus.ack_i:
                outstanding.next = False

            if not run:
                run.next = True # Comming out of reset 
            else: 
                if valid: # reset jump_taken when valid fetch
                    jump_taken.next = False

                if ( not outstanding or ibus.ack_i ) and new_jump: # a new jump resets the fetch unit
                    assert self.jump_dest_i[2:]==0,"misaligned jump detected"
                    ip.next = self.jump_dest_i
                    jump_taken.next = True
                    valid.next = False
                    busy.next = False 
                else:    
                    if  not ( ibus.stall_i or busy or self.stall_i ): # if nothing blocks us, update ip 
                        current_ip[2].next = ip
                        ip.next = ip + 4

                    if self.stall_i:
                        # Store pending fetch when next stage is stalled and block ourself
                        if ibus.ack_i:
                            current_word[1].next = ibus.db_rd
                            current_ip[1].next = current_ip[2]
                            busy.next = True
                    else:
                        if busy:
                            assert not ibus.ack_i, "Fetch: ack_i while busy asserted"
                            current_word[0].next = current_word[1]
                            #current_word[1].next=0 # debug only
                            current_ip[0].next = current_ip[1]
                            valid.next = True
                            busy.next = False
                        else:
                            if ibus.ack_i and not new_jump:
                                current_word[0].next = ibus.db_rd
                                current_ip[0].next = current_ip[2]
                                valid.next = True
                            else:    
                                valid.next = False 


        return instances()

"""
RISC-V execution stage
(c) 2019 The Bonfire Project
License: See LICENSE
"""

from myhdl import *

import alu

class ExecuteBundle:
    def __init__(self,config):
        #config
        self.config = config 

        xlen = config.xlen 

        #functional units
        self.alu=alu.AluBundle(xlen)

        #output
        self.result_o = Signal(intbv(0)[xlen:])
        self.reg_we_o = Signal(bool(0)) # Register File Write Enable
        self.rd_adr_o =  Signal(modbv(0)[5:]) # Target register 

        #pipeline control 

        self.en_i = Signal(bool(0)) # Input enable / valid
        self.busy_o = Signal(bool(0)) # unit busy (stall previous stage)
        self.valid_o = Signal(bool(0)) # Output valid
        #self.stall_i = Signal(bool(0)) # Stall input from next stage




    @block
    def SimpleExecute(self,decode,clock,reset):
        """
        Simple execution Unit designed for single stage in-order execution 
        decode : DecodeBundle class instance
        clock : clock
        reset : reset
        """

        alu_inst = self.alu.alu(clock,reset,self.config.shifter_mode )

        #busy =  Signal(bool(0))

        @always_comb
        def comb():


            # ALU Input wirings 
            self.alu.funct3_i.next = decode.funct3_o
            self.alu.funct7_6_i.next = decode.funct7_o[5]
            self.alu.op1_i.next = decode.op1_o
            self.alu.op2_i.next = decode.op2_o 

            # Functional Unit selection   
            self.alu.en_i.next = decode.alu_cmd

            # Stall handling
            b = decode.alu_cmd and self.alu.busy_o
            #busy.next = _busy 
            #TODO : Add other functional units 

            self.busy_o.next = b

            self.valid_o.next = not b and self.alu.valid_o

            self.rd_adr_o.next = decode.rd_adr_o 

            # Output multiplexers 

            if self.alu.valid_o:
                self.result_o.next = self.alu.res_o
            else:
                self.result_o.next = 0     
                
            self.reg_we_o.next = not b and  self.alu.valid_o  

            #TODO: Implement other functional units 
                

        return instances()
            

        





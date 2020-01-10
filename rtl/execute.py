"""
RISC-V execution stage
(c) 2019 The Bonfire Project
License: See LICENSE
"""

from myhdl import *

import alu
import loadstore

from instructions import BranchFunct3  as b3
from instructions import Opcodes

class ExecuteBundle:
    def __init__(self,config):
        #config
        self.config = config

        xlen = config.xlen

        #functional units
        self.alu=alu.AluBundle(xlen)
        self.ls = loadstore.LoadStoreBundle(config)

        #output
        self.result_o = Signal(intbv(0)[xlen:])
        self.reg_we_o = Signal(bool(0)) # Register File Write Enable
        self.rd_adr_o =  Signal(modbv(0)[5:]) # Target register

        self.jump_o = Signal(bool(0)) # Branch/jump
        self.jump_dest_o = Signal(intbv(0)[xlen:])

        self.invalid_opcode_fault = Signal(bool(0))

        #pipeline control

        self.en_i = Signal(bool(0)) # Input enable / valid
        self.busy_o = Signal(bool(0)) # unit busy (stall previous stage)
        self.valid_o = Signal(bool(0)) # Output valid
        #self.stall_i = Signal(bool(0)) # Stall input from next stage




    @block
    def SimpleExecute(self, decode, databus, clock, reset):
        """
        Simple execution Unit designed for single stage in-order execution
        decode : DecodeBundle class instance
        databus : DBusBundle instance  
        clock : clock
        reset : reset
        """

        assert self.config.loadstore_outstanding==1, "SimpleExecute requires config.loadstore_outstanding==1"

        busy = Signal(bool(0))

        alu_inst = self.alu.alu(clock,reset,self.config.shifter_mode )
        ls_inst = self.ls.LoadStoreUnit(databus,clock,reset)

        @always_comb
        def busy_proc():
            busy.next =  self.alu.busy_o or self.ls.busy_o


        @always_seq(clock.posedge,reset=reset)
        def seq():
            if self.en_i and not busy:
                self.rd_adr_o.next = decode.rd_adr_o

        
        @always_comb
        def comb():

            # Init
            self.invalid_opcode_fault.next = False
            self.jump_o.next=False
            self.jump_dest_o.next=0

            # ALU Input wirings
            self.alu.funct3_i.next = decode.funct3_o
            self.alu.funct7_6_i.next = decode.funct7_o[5]
            self.alu.op1_i.next = decode.op1_o
            self.alu.op2_i.next = decode.op2_o

            # LS Unit Input wirings
            self.ls.funct3_i.next = decode.funct3_o
            self.ls.op1_i.next = decode.op1_o
            self.ls.op2_i.next = decode.op2_o
            self.ls.displacement_i.next = decode.displacement_o
            self.ls.store_i.next = decode.store_cmd



            # Functional Unit selection
            if decode.valid_o and not busy:
                self.alu.en_i.next = decode.alu_cmd
                self.ls.en_i.next = decode.store_cmd or decode.load_cmd 

           # Output handling 
            
            self.busy_o.next = busy
            self.valid_o.next = self.alu.valid_o or self.ls.valid_o


            # Output multiplexers

            if self.alu.valid_o:
                self.result_o.next = self.alu.res_o
            elif decode.jump_cmd or decode.jumpr_cmd:
                self.result_o.next = decode.next_ip_o
            elif self.ls.valid_o:
                self.result_o.next = self.ls.result_o    
            else:
                self.result_o.next = 0

            self.reg_we_o.next = not busy and  self.alu.valid_o

            if decode.branch_cmd:

                f3 = decode.funct3_o
                if f3==b3.RV32_F3_BEQ:
                    self.jump_o.next = self.alu.flag_equal
                elif f3==b3.RV32_F3_BGE:
                    self.jump_o.next = self.alu.flag_ge
                elif f3==b3.RV32_F3_BGEU:
                    self.jump_o.next = self.alu.flag_uge
                elif f3==b3.RV32_F3_BLT:
                    self.jump_o.next = not self.alu.flag_ge
                elif f3==b3.RV32_F3_BLTU:
                    self.jump_o.next = not self.alu.flag_uge
                elif f3==b3.RV32_F3_BNE:
                    self.jump_o.next = not self.alu.flag_equal
                else:
                    self.invalid_opcode_fault.next = True

                self.jump_dest_o.next = decode.jump_dest_o
            elif decode.jump_cmd:
                self.jump_dest_o.next = decode.jump_dest_o
                self.jump_o.next = True
            elif decode.jumpr_cmd:
                self.jump_dest_o.next = self.alu.res_o

            #TODO: Implement other functional units


        return instances()

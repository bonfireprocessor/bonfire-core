"""
RISC-V execution stage
(c) 2019 The Bonfire Project
License: See LICENSE
"""

from myhdl import *

import alu

from instructions import BranchFunct3  as b3

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

        self.jump_o = Signal(bool(0)) # Branch/jump
        self.jump_dest_o = Signal(intbv(0)[xlen:])

        self.invalid_opcode_fault = Signal(bool(0))

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

            # Init
            self.invalid_opcode_fault.next = False
            self.jump_o.next=False
            self.jump_dest_o.next=0

            # ALU Input wirings
            self.alu.funct3_i.next = decode.funct3_o
            self.alu.funct7_6_i.next = decode.funct7_o[5]
            self.alu.op1_i.next = decode.op1_o
            self.alu.op2_i.next = decode.op2_o


            # Functional Unit selection
            self.alu.en_i.next = decode.alu_cmd

            # Stall handling
            busy = decode.alu_cmd and self.alu.busy_o

            #TODO : Add other functional units

            self.busy_o.next = busy
            self.valid_o.next = not busy and self.alu.valid_o

            self.rd_adr_o.next = decode.rd_adr_o

            # Output multiplexers

            if self.alu.valid_o:
                self.result_o.next = self.alu.res_o
            elif decode.jump_cmd or decode.jumpr_cmd:
                self.result_o.next = decode.next_ip_o
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

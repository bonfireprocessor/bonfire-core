"""
RISC-V execution stage
(c) 2019 The Bonfire Project
License: See LICENSE
"""
from __future__ import print_function

from myhdl import *

from rtl import alu, loadstore

from rtl.instructions import BranchFunct3  as b3
from rtl.instructions import Opcodes

from rtl.pipeline_control import *


class ExecuteBundle(PipelineControl):
    def __init__(self,config):
        #config
        self.config = config

        xlen = config.xlen

        #functional units
        self.alu=alu.AluBundle(xlen)
        self.ls = loadstore.LoadStoreBundle(config)

        # output
        self.result_o = Signal(intbv(0)[xlen:])
        self.reg_we_o = Signal(bool(0)) # Register File Write Enable
        self.rd_adr_o =  Signal(modbv(0)[5:]) # Target register

        self.jump_o = Signal(bool(0)) # Branch/jump
        self.jump_dest_o = Signal(intbv(0)[xlen:])

        self.invalid_opcode_fault = Signal(bool(0))

        # debug
        self.debug_exec_jump = Signal(bool(0))

        PipelineControl.__init__(self)



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
        valid = Signal(bool(0))
        rd_adr_reg = Signal(modbv(0)[5:])

        jump = Signal(bool(0))
        jump_r =  Signal(bool(0))
        jump_dest =  Signal(intbv(0)[self.config.xlen:])
        jump_dest_r = Signal(intbv(0)[self.config.xlen:])
        jump_busy = Signal(bool(0)) # Only used when not config.jump_bypass

        jump_we = Signal(bool(0)) # rd write enable on jal/jalr

        alu_inst = self.alu.alu(clock,reset,self.config.shifter_mode )
        ls_inst = self.ls.LoadStoreUnit(databus,clock,reset)

        p_inst = self.pipeline_instance(busy,valid)

        
        @always_seq(clock.posedge,reset=reset)
        def seq():

            jump_busy.next = False
            if self.taken:
                rd_adr_reg.next = decode.rd_adr_o
                jump_dest_r.next = jump_dest
                jump_r.next = jump
                jump_busy.next = jump and not self.config.jump_bypass
                   
                
                # # Debug code
                # if self.debug_exec_jump.next: 
                #     print(now(), "jump or branch")    
                
        @always_comb
        def comb():

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

            # Pipeline  
            busy.next = self.alu.busy_o or self.ls.busy_o or jump_busy
            valid.next = self.alu.valid_o or self.ls.valid_o  or jump_we

            if self.config.jump_bypass:
                decode.kill_i.next =  self.taken and jump
            else:    
                decode.kill_i.next = jump_busy


            # Functional Unit selection

            self.alu.en_i.next = decode.alu_cmd and self.taken
            self.ls.en_i.next = ( decode.store_cmd or decode.load_cmd ) and self.taken

            self.debug_exec_jump.next = self.taken and ( decode.branch_cmd or decode.jump_cmd or decode.jumpr_cmd )
    
           
        @always_comb
        def mux():   
            # Output multiplexers

            if self.taken and jump_we:
                self.result_o.next = decode.next_ip_o
            elif self.alu.valid_o:
                self.result_o.next = self.alu.res_o
           
            elif self.ls.valid_o:
                self.result_o.next = self.ls.result_o
            else:
                self.result_o.next = 0

            self.reg_we_o.next =  self.alu.valid_o or self.ls.we_o  or jump_we

            if self.taken:
                self.rd_adr_o.next = decode.rd_adr_o
            else:
                self.rd_adr_o.next = rd_adr_reg

            if self.taken and self.config.jump_bypass:  
                self.jump_o.next = jump
                self.jump_dest_o.next = jump_dest
            else:
                self.jump_o.next = jump_r and not self.taken # supress jump_o when next instruction after jump is taken
                self.jump_dest_o.next = jump_dest_r

                     
        @always_comb
        def jump_comb():

            self.invalid_opcode_fault.next = False
            jump.next = False
            jump_dest.next = 0
            jump_we.next = False
            if self.en_i and self.taken:
                if decode.branch_cmd:

                    f3 = decode.funct3_o
                    if f3==b3.RV32_F3_BEQ:
                        jump.next = self.alu.flag_equal
                    elif f3==b3.RV32_F3_BGE:
                        jump.next = self.alu.flag_ge
                    elif f3==b3.RV32_F3_BGEU:
                        jump.next = self.alu.flag_uge
                    elif f3==b3.RV32_F3_BLT:
                        jump.next = not self.alu.flag_ge
                    elif f3==b3.RV32_F3_BLTU:
                        jump.next = not self.alu.flag_uge
                    elif f3==b3.RV32_F3_BNE:
                        jump.next = not self.alu.flag_equal
                    else:
                        self.invalid_opcode_fault.next = True

                    jump_dest.next = decode.jump_dest_o
                elif decode.jump_cmd:
                    jump_dest.next = decode.jump_dest_o
                    jump.next = True
                    jump_we.next = True 
                elif decode.jumpr_cmd:
                    jump_dest.next = self.alu.res_o
                    jump.next = True
                    jump_we.next = True 
            
                    
            


            #TODO: Implement other functional units


        return instances()

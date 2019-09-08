"""
RISC-V instruction decoder
(c) 2019 The Bonfire Project
License: See LICENSE
"""

from myhdl import *
from instructions import Opcodes as op
from instructions import ArithmeticFunct3  as f3 
from util import signed_resize 


def get_I_immediate(instr):
    #return concat(instr[32:20])
    return modbv(instr[32:20])[12:]


def get_U_immediate(instr):
    return concat(instr[32:12],intbv(0)[12:])


def get_UJ_immediate(instr):
    return concat(instr[31],instr[20:12],instr[20],instr[31:21],intbv(0)[1:])


def get_S_immediate(instr):
    return concat(instr[32:25],instr[12:7])


def get_SB_immediate(instr):
    return concat(instr[31],instr[7],instr[31:25],instr[12:8],intbv(0)[1:])
    




class Decoder:
    def __init__(self,xlen=32):
        self.word_i = Signal(intbv(0)[xlen:]) # actual instruction to decode
        self.next_ip_i = Signal(modbv(0)[xlen:]) # ip (PC) of next instruction

        # Register file interface
        # Register data will be delayed by one clock !
        self.rs1_data_i = Signal(modbv(0)[xlen:])
        self.rs2_data_i = Signal(modbv(0)[xlen:])

        self.rs1_adr_o = Signal(modbv(0)[5:])
        self.rs2_adr_o = Signal(modbv(0)[5:])

        self.rs1_adr_o_reg = Signal(modbv(0)[5:])
        self.rs2_adr_o_reg = Signal(modbv(0)[5:])

        # Output to execute stage
        self.op1_o = Signal(modbv(0)[xlen:])
        self.op2_o = Signal(modbv(0)[xlen:])
        #self.op3_o = Signal(modbv(0)[xlen:])

        self.rd_adr_o =  Signal(modbv(0)[5:])

        self.funct3_o = Signal(intbv(0)[3:])
        self.funct7_o = Signal(intbv(0)[7:])
        self.displacement_o = Signal(intbv(0)[12:])
        self.branch_displacement = Signal(intbv(0)[13:])

        # Functional unit control
        self.alu_cmd = Signal(bool(0))
        self.load_store_cmd = Signal(bool(0))
        self.branch_cmd = Signal(bool(0))
        self.jump_cmd = Signal(bool(0))
        self.csr_cmd = Signal(bool(0))
        self.invalid_opcode = Signal(bool(0))

        # Control Signals
        self.en_i = Signal(bool(0)) # Input enable / valid
        self.busy_o = Signal(bool(0)) # Decoder busy (stall previous stage)
        self.valid_o = Signal(bool(0)) # Output valid
        self.stall_i = Signal(bool(0)) # Stall input from next stage

        # Debug
        self.debug_word_o = Signal(intbv(0)[xlen:])

        # Constants
        self.xlen = xlen

    @block
    def decoder(self,clock,reset):
        
        opcode=Signal(intbv(0)[5:])

        rs2_immediate=Signal(bool(0)) # rs2 Operand is an immediate
        rs2_imm_value=Signal(modbv(0)[self.xlen:])

        rs1_immediate=Signal(bool(0)) # rs1 Operand is an immediate
        rs1_imm_value=Signal(modbv(0)[self.xlen:])
        
        @always_comb
        def comb():
            self.rs1_adr_o.next = self.word_i[20:15]
            self.rs2_adr_o.next = self.word_i[25:20]

            opcode.next=self.word_i[7:2]
            self.busy_o.next = self.stall_i

            # Operand output side 
           
            if rs2_immediate:
                self.op2_o.next = rs2_imm_value
            else:  
                self.op2_o.next = self.rs2_data_i
            
            if rs1_immediate:
                self.op1_o.next = rs1_imm_value
            else:  
               self.op1_o.next = self.rs1_data_i    


        @always_seq(clock.posedge,reset=reset)
        def decode_op():

            
            if self.en_i and not self.stall_i:
                inv=False 

                self.debug_word_o.next = self.word_i 
               
                self.funct3_o.next = self.word_i[15:12]
                self.funct7_o.next = self.word_i[32:25]
                self.rd_adr_o.next = self.word_i[12:7]

                self.rs1_adr_o_reg.next = self.word_i[20:15]
                self.rs2_adr_o_reg.next = self.word_i[25:20]

                self.displacement_o.next = 0 
                rs1_immediate.next = False 

                self.alu_cmd.next = False
                self.branch_cmd.next = False
                self.jump_cmd.next = False
                

                if self.word_i[2:0]!=3:
                    inv=True 

                elif opcode==op.RV32_OP:
                    print "RV32_OP"
                    self.alu_cmd.next = True
                    rs2_immediate.next = False 

                elif opcode==op.RV32_IMM:
                    self.alu_cmd.next = True
                    rs2_imm_value.next = signed_resize(get_I_immediate(self.word_i),self.xlen)
                    rs2_immediate.next = True 

                elif opcode==op.RV32_BRANCH:
                    self.branch_cmd.next = True   
                    self.branch_displacement.next =  get_SB_immediate(self.word_i)
                    rs2_immediate.next = False 
                    
                elif opcode==op.RV32_JAL:
                    self.jump_cmd.next = True
                    rs1_imm_value.next = signed_resize(get_UJ_immediate(self.word_i),self.xlen)
                    rs1_immediate.next = True
                    rs2_imm_value.next = self.next_ip_i 
                    rs1_immediate.next = True 

                elif opcode==op.RV32_JALR:
                    self.jump_cmd.next = True
                    rs2_imm_value.next = self.next_ip_i 
                    rs2_immediate.next = True  
                    self.displacement_o.next = get_I_immediate(self.word_i)
                
                elif opcode==op.RV32_LUI or opcode==op.RV32_AUIPC:
                    self.alu_cmd.next = True
                    rs1_immediate.next = True 
                    rs1_imm_value.next = signed_resize(get_U_immediate(self.word_i),self.xlen) 
                    rs2_immediate.next = True
                    if opcode==op.RV32_AUIPC:
                        rs2_imm_value.next = self.next_ip_i
                    else:
                        rs2_imm_value.next=0 
                    self.funct3_o.next =  f3.RV32_F3_ADD_SUB
                    self.funct7_o.next = 0        


                else:
                    inv=True 

            
                self.valid_o.next = not inv
                self.invalid_opcode.next= inv 


        return instances()            
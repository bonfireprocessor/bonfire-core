"""
RISC-V instruction decoder
(c) 2019 The Bonfire Project
License: See LICENSE
"""

from myhdl import *
from instructions import Opcodes as op

def get_I_immediate(instr):
    return instr[32:20]


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
        self.word_i = Signal(modbv(0)[xlen:]) # actual instruction to decode
        self.next_ip_i = Signal(modbv(0)[xlen:]) # ip (PC) of next instruction

        # Register file interface
        # Register data will be delayed by one clock !
        self.rs1_data_i = Signal(modbv(0)[xlen:])
        self.rs2_data_i = Signal(modbv(0)[xlen:])

        self.rs1_adr_o = Signal(modbv(0)[5:])
        self.rs2_adr_o = Signal(modbv(0)[5:])

        # Output to execute stage
        self.op1_o = Signal(modbv(0)[xlen:])
        self.op2_o = Signal(modbv(0)[xlen:])
        self.op3_o = Signal(modbv(0)[xlen:])

        self.rd_adr_o =  Signal(modbv(0)[5:])

        self.funct3_o=Signal(intbv(0)[3:])
        self.funct7_o=Signal(intbv(0)[7:])
        self.displacement_o = Signal(intbv(0)[12:])

        # Functional unit control
        self.alu_cmd = Signal(bool(0))
        self.load_store_cmd = Signal(bool(0))
        self.branch_cmd = Signal(bool(0))
        self.jump_cmd = Signal(bool(0))
        self.csr_cmd = Signal(bool(0))

        # Control Signals
        self.en_i=Signal(bool(0)) # Input enable / valid
        self.busy_o=Signal(bool(0)) # Decoder busy (stall previous stage)
        self.valid_o=Signal(bool(0)) # Output valid
        self.stall_i = Signal(bool(0)) # Stall input from next stage

        # Constants
        self.xlen = xlen

    @block
    def decoder(self,clock,reset):
        
        opcode=Signal(intbv(0)[5:])
        
        @always_comb
        def comb()
            self.rs1_adr_o.next = self.word_i[20:15]
            self.rs2_adr_o.next = self.word_i[25:20]
            
            opcode=self.word_i[7:2]
            self.busy_o.next = self.stall_i


        @always_seq(clock.posedge,reset=reset)
        def decode_op():
            
            if self.en_i and not self.stall_i:
                self.funct3_o.next = self.word_i[15:12]
                self.funct7_o.next = self.word_i[32:25]
                self.rd_adr_o.next = self.word_i[12:7]

                if opcode==op.RV32_OP:
                    self.alu_cmd.next = True
                    self.op1_o.next = self.rs1_data_i
                    self.op2_o.next = self.rs2_data_i

                elif opcode==op.RV32_IMM:
                    self.alu_cmd.next = True
                    self.op1_o.next = self.rs1_data_i
                    self.op2_o.next = get_I_immediate(self.word_i)
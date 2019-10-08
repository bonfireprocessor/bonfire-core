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
    res = intbv(0)[12:]
    res[:] = instr[32:20]
    return res


def get_U_immediate(instr):
    return concat(instr[32:12],intbv(0)[12:])


def get_UJ_immediate(instr):
    return concat(instr[31],instr[20:12],instr[20],instr[31:21],intbv(0)[1:])


def get_S_immediate(instr):
    return concat(instr[32:25],instr[12:7])


def get_SB_immediate(instr):
    return concat(instr[31],instr[7],instr[31:25],instr[12:8],intbv(0)[1:])



class DecodeBundle:
    def __init__(self,xlen=32):
        self.word_i = Signal(intbv(0)[xlen:]) # actual instruction to decode
        self.current_ip_i = Signal(modbv(0)[xlen:])
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
        #self.op3_o = Signal(modbv(0)[xlen:])

        self.rd_adr_o =  Signal(modbv(0)[5:])

        self.funct3_onehot_o = Signal(intbv(1)[8:])
        self.funct7_o = Signal(intbv(0)[7:])
        self.displacement_o = Signal(intbv(0)[12:])
        self.jump_dest_o = Signal(modbv(0)[xlen:])
        self.next_ip_o = Signal(modbv(0)[xlen:])

        # Functional unit control
        self.alu_cmd = Signal(bool(0))
        self.load_store_cmd = Signal(bool(0))
        self.branch_cmd = Signal(bool(0))
        self.jump_cmd = Signal(bool(0))
        self.jumpr_cmd = Signal(bool(0))
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

        opcode = Signal(intbv(0)[5:])

        rs2_immediate = Signal(bool(0)) # rs2 Operand is an immediate
        rs2_imm_value = Signal(modbv(0)[self.xlen:])

        rs1_immediate = Signal(bool(0)) # rs1 Operand is an immediate
        rs1_imm_value = Signal(modbv(0)[self.xlen:])

        rs1_adr_o_reg = Signal(modbv(0)[5:])
        rs2_adr_o_reg = Signal(modbv(0)[5:])

        downstream_busy = Signal(bool(0))

        @always_comb
        def busy_control():
            downstream_busy.next = self.valid_o and self.stall_i


        @always_comb
        def comb():

            if not downstream_busy:
                self.rs1_adr_o.next = self.word_i[20:15]
                self.rs2_adr_o.next = self.word_i[25:20]
            else:
                self.rs1_adr_o.next = rs1_adr_o_reg
                self.rs2_adr_o.next = rs2_adr_o_reg

            opcode.next=self.word_i[7:2]
            self.busy_o.next = downstream_busy



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


            if self.en_i and not downstream_busy:
                inv=False

                self.debug_word_o.next = self.word_i

                self.funct3_onehot_o.next=0 
                index=int(self.word_i[15:12])
                self.funct3_onehot_o.next[index]=True 
                
                self.funct7_o.next = self.word_i[32:25]
                self.rd_adr_o.next = self.word_i[12:7]

                rs1_adr_o_reg.next = self.word_i[20:15]
                rs2_adr_o_reg.next = self.word_i[25:20]

                self.next_ip_o.next = self.next_ip_i 

                self.displacement_o.next = 0
                rs1_immediate.next = False
                rs2_immediate.next = False

                self.alu_cmd.next = False
                self.branch_cmd.next = False
                self.jump_cmd.next = False
                self.jumpr_cmd.next = False
                self.load_store_cmd.next = False
                self.csr_cmd.next = False

                if self.word_i[2:0]!=3:
                    inv=True

                elif opcode==op.RV32_OP:
                    print "RV32_OP"
                    self.alu_cmd.next = True
                   

                elif opcode==op.RV32_IMM:
                    self.alu_cmd.next = True
                    rs2_imm_value.next = signed_resize(get_I_immediate(self.word_i),self.xlen)
                    rs2_immediate.next = True

                elif opcode==op.RV32_BRANCH:
                    self.branch_cmd.next = True
                    self.jump_dest_o.next = self.current_ip_i + get_SB_immediate(self.word_i).signed()
                   
                    self.branch_cmd.next=True

                elif opcode==op.RV32_JAL:
                    self.jump_cmd.next = True
                    self.jump_dest_o.next = self.current_ip_i + get_UJ_immediate(self.word_i).signed()

                elif opcode==op.RV32_JALR:
                    self.jumpr_cmd.next = True
                     # Use ALU to calculate target 
                    self.alu_cmd.next = True
                    self.funct3_onehot_o.next = 2**f3.RV32_F3_ADD_SUB   
                    rs2_imm_value.next =  get_I_immediate(self.word_i).signed()
                    rs2_immediate.next = True
                    
                elif opcode==op.RV32_LUI or opcode==op.RV32_AUIPC:
                    self.alu_cmd.next = True
                    rs1_immediate.next = True
                    rs1_imm_value.next = get_U_immediate(self.word_i)
                    rs2_immediate.next = True
                    if opcode==op.RV32_AUIPC:
                        rs2_imm_value.next = self.next_ip_i
                    else:
                        rs2_imm_value.next=0

                    self.funct3_onehot_o.next = 2**f3.RV32_F3_ADD_SUB   
                    self.funct7_o.next = 0

                else:
                    inv=True


                self.valid_o.next = not inv
                self.invalid_opcode.next= inv


        return instances()
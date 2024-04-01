"""
RISC-V instruction decoder
(c) 2019 The Bonfire Project
License: See LICENSE
"""

from myhdl import *
from rtl.instructions import Opcodes as op
from rtl.instructions import ArithmeticFunct3  as f3
from rtl.instructions import SystemFunct3
from rtl.util import signed_resize
from rtl.debugModule import *

from rtl.pipeline_control import *


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



class DecodeBundle(PipelineControl):
    def __init__(self,xlen=32):
        self.word_i = Signal(modbv(0)[xlen:]) # actual instruction to decode
        self.current_ip_i = Signal(modbv(0)[xlen:])
        self.next_ip_i = Signal(modbv(0)[xlen:]) # ip (PC) of next instruction
        self.kill_i = Signal(bool(0)) # kill current instruction


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
        self.funct3_o = Signal(intbv(0)[3:])
        self.funct7_o = Signal(intbv(0)[7:])
        self.displacement_o = Signal(intbv(0)[12:])
        self.jump_dest_o = Signal(modbv(0)[xlen:])
        self.next_ip_o = Signal(modbv(0)[xlen:])
        self.priv_funct_12 = Signal(modbv(0)[12:])
        self.mepc_o = Signal(modbv(0)[xlen:])

        # Functional unit control
        self.alu_cmd = Signal(bool(0))
        self.load_cmd = Signal(bool(0))
        self.store_cmd = Signal(bool(0))
        self.branch_cmd = Signal(bool(0))
        self.jump_cmd = Signal(bool(0))
        self.jumpr_cmd = Signal(bool(0))
        self.csr_cmd = Signal(bool(0))
        self.sys_cmd = Signal(bool(0))
        self.invalid_opcode = Signal(bool(0))


        # Debug
        self.debug_word_o = Signal(intbv(0)[xlen:])
        self.debug_current_ip_o = Signal(intbv(0)[xlen:])

        # Constants
        self.xlen = xlen

        PipelineControl.__init__(self)

    @block
    def decoder(self,clock,reset,debugRegisterBundle=None):

        opcode = Signal(intbv(0)[5:])

        rs2_immediate = Signal(bool(0)) # rs2 Operand is an immediate
        rs2_imm_value = Signal(modbv(0)[self.xlen:])

        rs1_immediate = Signal(bool(0)) # rs1 Operand is an immediate
        rs1_imm_value = Signal(modbv(0)[self.xlen:])

        rs1_adr_o_reg = Signal(modbv(0)[5:])
        rs2_adr_o_reg = Signal(modbv(0)[5:])

        downstream_busy = Signal(bool(0))

        dm_halt = Signal(bool(0))
        dm_halt_req = Signal(bool(0))
        dm_resume_req = Signal(bool(0))
        dm_kill = Signal(bool(0))
        dm_regwrite = Signal(bool(0))
        dm_regno = Signal(modbv(0)[5:])
        dm_data0 = Signal(modbv(0)[32:])

        ins_word=Signal(modbv(0)[32:]) # instructoo to decode

        @always_comb
        def busy_control():
            downstream_busy.next = self.valid_o and self.stall_i


        @always_comb
        def comb():

            ins_word.next = self.word_i

            #rs 1 Mux is moved downwards to the conditional code for the Debug Module
            if not downstream_busy:
                #self.rs1_adr_o.next = self.word_i[20:15]
                self.rs2_adr_o.next = ins_word[25:20]
            else:
                #self.rs1_adr_o.next = rs1_adr_o_reg
                self.rs2_adr_o.next = rs2_adr_o_reg

            opcode.next=ins_word[7:2]
            self.busy_o.next = downstream_busy or dm_halt or dm_halt_req


            # Operand output side

            if rs2_immediate:
                self.op2_o.next = rs2_imm_value
            else:
                self.op2_o.next = self.rs2_data_i

            if rs1_immediate:
                self.op1_o.next = rs1_imm_value
            else:
               self.op1_o.next = self.rs1_data_i


        if  debugRegisterBundle:
            conf=debugRegisterBundle.config

            @always_comb
            def rs1_mux():

                dm_regwrite.next = False
                dm_data0.next = debugRegisterBundle.dataRegs[0]
                dm_regno.next = debugRegisterBundle.regno

                if debugRegisterBundle.abstractCommandState==t_abstractCommandState.new \
                   and debugRegisterBundle.commandType==t_abstractCommandType.access_reg:

                    dm_regwrite.next = debugRegisterBundle.write

                    self.rs1_adr_o.next = debugRegisterBundle.regno

                elif not downstream_busy:
                    self.rs1_adr_o.next = ins_word[20:15]
                else:
                    self.rs1_adr_o.next = rs1_adr_o_reg



            @always(clock.posedge) # Debug Unit is indepedeant of processsor reset
            def debug_module_seq():


                if debugRegisterBundle.dpc_jump:
                    debugRegisterBundle.dpc_jump.next=False

                if not downstream_busy:

                    if debugRegisterBundle.haltreq:
                        debugRegisterBundle.haltreq.next=False
                        debugRegisterBundle.dpc.next=self.current_ip_i[conf.xlen:conf.ip_low]
                        dm_halt.next = True
                    elif debugRegisterBundle.resumereq:
                        debugRegisterBundle.resumereq.next=False
                        dm_halt.next = False
                        debugRegisterBundle.dpc_jump.next=True

                if dm_halt:
                    if debugRegisterBundle.commandType==t_abstractCommandType.access_reg:
                        if debugRegisterBundle.abstractCommandState==t_abstractCommandState.new:
                            debugRegisterBundle.abstractCommandState.next=t_abstractCommandState.done

                        if debugRegisterBundle.abstractCommandState==t_abstractCommandState.done:
                            if not debugRegisterBundle.write:
                                debugRegisterBundle.dataRegs[0].next = self.rs1_data_i
                            debugRegisterBundle.abstractCommandState.next = t_abstractCommandState.none

            @always_comb
            def dm_state():
                dm_halt_req.next = debugRegisterBundle.haltreq
                dm_resume_req.next = debugRegisterBundle.resumereq
                dm_kill.next = debugRegisterBundle.dpc_jump

                if dm_halt:
                    debugRegisterBundle.hartState.next=t_debugHartState.halted
                else:
                    debugRegisterBundle.hartState.next=t_debugHartState.running

        else: # no Debug Module
            @always_comb
            def rs1_mux():

                if not downstream_busy:
                    self.rs1_adr_o.next = ins_word[20:15]
                else:
                    self.rs1_adr_o.next = rs1_adr_o_reg



        @always_seq(clock.posedge,reset=reset)
        def decode_op():

            """
            When kill_i, invalidate output stage else
            While downstream_busy do nothing
            otherwise decode the next instruction when en_i is set
            """

            if dm_halt and dm_regwrite:
                # Inject GPR Write into the pipeline
                self.valid_o.next = True
                rs1_immediate.next = True
                rs2_immediate.next = True
                rs1_imm_value.next = dm_data0
                rs2_imm_value.next = 0
                self.alu_cmd.next = True
                self.funct3_o.next = f3.RV32_F3_OR
                self.rd_adr_o.next = dm_regno

                self.debug_word_o.next=0

                self.branch_cmd.next = False
                self.jump_cmd.next = False
                self.jumpr_cmd.next = False
                self.load_cmd.next = False
                self.store_cmd.next = False
                self.csr_cmd.next = False
                self.invalid_opcode.next = False
                self.sys_cmd.next = False




            elif self.kill_i or dm_kill or dm_halt or dm_halt_req:
                self.valid_o.next = False
                self.invalid_opcode.next = False

            elif not downstream_busy:
                if self.en_i:
                    inv=False

                    self.debug_word_o.next = ins_word
                    self.debug_current_ip_o.next = self.current_ip_i

                    self.funct3_o.next = ins_word[15:12]
                    self.funct3_onehot_o.next = 0
                    index = int(ins_word[15:12])
                    self.funct3_onehot_o.next[index] = True

                    self.funct7_o.next = ins_word[32:25]
                    self.rd_adr_o.next = ins_word[12:7]

                    rs1_adr_o_reg.next = ins_word[20:15]
                    rs2_adr_o_reg.next = ins_word[25:20]

                    self.next_ip_o.next = self.next_ip_i

                    #self.displacement_o.next = 0
                    rs1_immediate.next = False
                    rs2_immediate.next = False

                    self.alu_cmd.next = False
                    self.branch_cmd.next = False
                    self.jump_cmd.next = False
                    self.jumpr_cmd.next = False
                    self.load_cmd.next = False
                    self.store_cmd.next = False
                    self.csr_cmd.next = False
                    self.invalid_opcode.next = False
                    self.sys_cmd.next = False

                    self.mepc_o.next = self.current_ip_i

                    if ins_word[2:0]!=3:
                        inv=True

                    elif opcode==op.RV32_OP:
                        self.alu_cmd.next = True
                    elif opcode==op.RV32_IMM:
                        self.alu_cmd.next = True
                        # Workaround for ADDI...
                        if ins_word[15:12]==f3.RV32_F3_ADD_SUB:
                            self.funct7_o.next[5] = False
                        rs2_imm_value.next = signed_resize(get_I_immediate(ins_word),self.xlen)
                        rs2_immediate.next = True

                    elif opcode==op.RV32_BRANCH:
                        self.branch_cmd.next = True
                        self.jump_dest_o.next = self.current_ip_i + get_SB_immediate(ins_word).signed()

                    elif opcode==op.RV32_JAL:
                        self.jump_cmd.next = True
                        self.jump_dest_o.next = self.current_ip_i + get_UJ_immediate(ins_word).signed()

                    elif opcode==op.RV32_JALR:
                        self.jumpr_cmd.next = True
                        # Use ALU to calculate target
                        self.alu_cmd.next = True
                        self.funct3_onehot_o.next = 2**f3.RV32_F3_ADD_SUB
                        self.funct3_o.next = f3.RV32_F3_ADD_SUB
                        self.funct7_o.next[5] = False
                        rs2_imm_value.next =  signed_resize(get_I_immediate(ins_word),self.xlen)
                        rs2_immediate.next = True

                    elif opcode==op.RV32_LUI or opcode==op.RV32_AUIPC:
                        self.alu_cmd.next = True
                        rs1_immediate.next = True
                        rs1_imm_value.next = get_U_immediate(ins_word)
                        rs2_immediate.next = True
                        if opcode==op.RV32_AUIPC:
                            rs2_imm_value.next = self.current_ip_i
                        else:
                            rs2_imm_value.next=0

                        self.funct3_onehot_o.next = 2**f3.RV32_F3_ADD_SUB
                        self.funct3_o.next = f3.RV32_F3_ADD_SUB
                        self.funct7_o.next = 0
                    elif opcode==op.RV32_STORE:
                        self.store_cmd.next = True
                        self.displacement_o.next = get_S_immediate(ins_word)
                    elif opcode==op.RV32_LOAD:
                        self.load_cmd.next = True
                        self.displacement_o.next = get_I_immediate(ins_word)
                    elif opcode==op.RV32_SYSTEM:
                        self.priv_funct_12.next = ins_word[32:20]
                        if ins_word[15:12]==SystemFunct3.RV32_F3_PRIV:
                            self.sys_cmd.next = True
                        else:
                            self.csr_cmd.next = True
                            if ins_word[14]: # Immediate
                                rs1_immediate.next = True
                                rs1_imm_value.next = ins_word[20:15]
                    else:
                        inv=True
                    self.valid_o.next = not inv
                    self.invalid_opcode.next= inv
                else:
                    self.valid_o.next=False

        return instances()
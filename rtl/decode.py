"""
RISC-V instruction decoder
(c) 2019 The Bonfire Project
License: See LICENSE
"""

from myhdl import *
from rtl.instructions import Opcodes as op
from rtl.instructions import ArithmeticFunct3  as f3
from rtl.instructions import SystemFunct3
from rtl.instructions import PrivFunct12
from rtl.util import signed_resize
from rtl.debugModule import *
from rtl.debug_control import DebugDecodeControlBundle, DebugDecodeController, DebugDecodeViewBundle

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
    def __init__(self,config=None):
        if config is None:
            from rtl.config import BonfireConfig
            self.config = BonfireConfig()
        else:
            self.config = config

        xlen = self.config.xlen
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

        if self.config.enableDebugModule:
            self.debugCSRBundle = DebugCSRBundle(self.config)
            self.debugCSRUpdateBundle = DebugCSRUpdateBundle(self.config)


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

        debug_decode_view = DebugDecodeViewBundle(self.config)
        debug_control = DebugDecodeControlBundle(self.config)

        # Local names are Python aliases to the bundle Signal objects. They do
        # not create extra logic; assignments to .next drive the original
        # Signal in the corresponding debug bundle.
        dm_halt = debug_control.halt
        dm_kill = debug_control.kill
        dm_regwrite = debug_control.regwrite
        dm_regno = debug_control.regno
        dm_data0 = debug_control.data0
        dm_exec = debug_control.exec
        dm_break = debug_decode_view.dm_break
        dm_ebreak_halt_req = debug_control.ebreak_halt_req
        dm_step_armed = debug_control.step_armed
        dm_step_halt_pending = debug_control.step_halt_pending

        ins_word = Signal(modbv(0)[32:])

        @always_comb
        def busy_control():
            downstream_busy.next = self.valid_o and self.stall_i


        @always_comb
        def comb():
            debug_decode_view.current_ip_i.next = self.current_ip_i
            debug_decode_view.word_i.next = self.word_i
            debug_decode_view.en_i.next = self.en_i
            debug_decode_view.kill_i.next = self.kill_i
            debug_decode_view.rs1_data_i.next = self.rs1_data_i
            debug_decode_view.valid_o.next = self.valid_o
            debug_decode_view.stall_i.next = self.stall_i
            debug_decode_view.downstream_busy.next = downstream_busy

            if not downstream_busy:
                self.rs2_adr_o.next = ins_word[25:20]
            else:
                self.rs2_adr_o.next = rs2_adr_o_reg

            self.busy_o.next = downstream_busy or dm_halt


            # Operand output side

            if rs2_immediate:
                self.op2_o.next = rs2_imm_value
            else:
                self.op2_o.next = self.rs2_data_i

            if rs1_immediate:
                self.op1_o.next = rs1_imm_value
            else:
               self.op1_o.next = self.rs1_data_i


        if self.config.enableDebugModule:
            conf = self.config
            assert debugRegisterBundle is not None, "enableDebugModule requires a debugRegisterBundle"

            progbuf=Signal(modbv(0)[conf.xlen:])
            progbuf_pointer=Signal(modbv(0)[1:]) # only 1 bit needed to select between progbuf0 and progbuf1
            progbuf_last = Signal(bool(0))


            if self.config.progbuf_size==2:
                @always_comb
                def progbuf_mux():
                    if progbuf_pointer:
                        progbuf.next = debugRegisterBundle.progbuf1
                        progbuf_last.next = True
                    else:
                        progbuf.next = debugRegisterBundle.progbuf0
                        progbuf_last.next = False

            else:
                @always_comb
                def progbuf_mux():
                    progbuf.next = debugRegisterBundle.progbuf0
                    progbuf_last.next = True

            @always_comb
            def comb2():

                temp_instr = self.word_i
                if dm_halt:
                    temp_instr = progbuf
                  
 
                ins_word.next = temp_instr
                opcode.next = temp_instr[7:2]

                if debugRegisterBundle.abstractCommandNew and \
                   debugRegisterBundle.abstractCommandState == t_abstractCommandState.none and \
                   debugRegisterBundle.commandType == t_abstractCommandType.access_reg:
                    self.rs1_adr_o.next = debugRegisterBundle.regno
                elif not downstream_busy:
                    self.rs1_adr_o.next = temp_instr[20:15]
                else:
                    self.rs1_adr_o.next = rs1_adr_o_reg

            debug_decode_inst = DebugDecodeController(
                self.config,
                clock,
                debugRegisterBundle,
                self.debugCSRBundle,
                self.debugCSRUpdateBundle,
                debug_decode_view,
                debug_control,
                progbuf_pointer,
                progbuf_last,
            )

        else:
            @always_comb
            def comb2():
                ins_word.next = self.word_i
                opcode.next = self.word_i[7:2]
                dm_halt.next = False
                dm_kill.next = False
                dm_regwrite.next = False
                dm_regno.next = 0
                dm_data0.next = 0
                dm_exec.next = False
                dm_ebreak_halt_req.next = False
                dm_step_armed.next = False
                dm_step_halt_pending.next = False

                if not downstream_busy:
                    self.rs1_adr_o.next = self.word_i[20:15]
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
                self.valid_o.next = True
                rs1_immediate.next = True
                rs2_immediate.next = True
                rs1_imm_value.next = dm_data0
                rs2_imm_value.next = 0
                self.alu_cmd.next = True
                self.funct3_o.next = f3.RV32_F3_OR
                self.rd_adr_o.next = dm_regno

                self.debug_word_o.next = 0

                self.branch_cmd.next = False
                self.jump_cmd.next = False
                self.jumpr_cmd.next = False
                self.load_cmd.next = False
                self.store_cmd.next = False
                self.csr_cmd.next = False
                self.invalid_opcode.next = False
                self.sys_cmd.next = False
                dm_break.next = False

            elif (self.kill_i or dm_kill or dm_halt or dm_ebreak_halt_req or dm_step_halt_pending) and not dm_exec:
                self.valid_o.next = False
                self.invalid_opcode.next = False
                dm_break.next = False
            elif not downstream_busy:
                if self.en_i or dm_exec:
                    inv=False
                    dm_break_seen = False
                    cmd_seen = False

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
                        cmd_seen = True
                    elif opcode==op.RV32_IMM:
                        self.alu_cmd.next = True
                        cmd_seen = True
                        # Workaround for ADDI...
                        if ins_word[15:12]==f3.RV32_F3_ADD_SUB:
                            self.funct7_o.next[5] = False
                        rs2_imm_value.next = signed_resize(get_I_immediate(ins_word),self.xlen)
                        rs2_immediate.next = True

                    elif opcode==op.RV32_BRANCH:
                        self.branch_cmd.next = True
                        cmd_seen = True
                        self.jump_dest_o.next = self.current_ip_i + get_SB_immediate(ins_word).signed()

                    elif opcode==op.RV32_JAL:
                        self.jump_cmd.next = True
                        cmd_seen = True
                        self.jump_dest_o.next = self.current_ip_i + get_UJ_immediate(ins_word).signed()

                    elif opcode==op.RV32_JALR:
                        self.jumpr_cmd.next = True
                        cmd_seen = True
                        # Use ALU to calculate target
                        self.alu_cmd.next = True
                        self.funct3_onehot_o.next = 2**f3.RV32_F3_ADD_SUB
                        self.funct3_o.next = f3.RV32_F3_ADD_SUB
                        self.funct7_o.next[5] = False
                        rs2_imm_value.next =  signed_resize(get_I_immediate(ins_word),self.xlen)
                        rs2_immediate.next = True

                    elif opcode==op.RV32_LUI or opcode==op.RV32_AUIPC:
                        self.alu_cmd.next = True
                        cmd_seen = True
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
                        cmd_seen = True
                        self.displacement_o.next = get_S_immediate(ins_word)
                    elif opcode==op.RV32_LOAD:
                        self.load_cmd.next = True
                        cmd_seen = True
                        self.displacement_o.next = get_I_immediate(ins_word)
                    elif opcode==op.RV32_FENCE:
                        # Treat FENCE/FENCE.I as a NOP in this core.
                        cmd_seen = True
                    elif opcode==op.RV32_SYSTEM:
                        self.priv_funct_12.next = ins_word[32:20]
                        if ins_word[15:12]==SystemFunct3.RV32_F3_PRIV:
                            if dm_exec and ins_word[32:20]==PrivFunct12.RV32_F12_EBREAK:
                                 dm_break_seen = True    
                            else:     
                                self.sys_cmd.next = True
                                cmd_seen = True
                        else:
                            self.csr_cmd.next = True
                            cmd_seen = True
                            if ins_word[14]: # Immediate
                                rs1_immediate.next = True
                                rs1_imm_value.next = ins_word[20:15]
                    else:
                        inv=True
                    self.valid_o.next = not inv and not dm_break_seen and cmd_seen
                    dm_break.next = dm_break_seen
                    self.invalid_opcode.next= inv
                else:
                    self.valid_o.next=False
                    dm_break.next = False

        return instances()

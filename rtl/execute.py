"""
RISC-V execution stage
(c) 2019 The Bonfire Project
License: See LICENSE
"""
from __future__ import print_function

from myhdl import *

from rtl import alu, loadstore, csr, trap

from rtl.instructions import ArithmeticFunct3 as a3
from rtl.instructions import BranchFunct3  as b3
from rtl.instructions import Opcodes, PrivFunct12

from rtl.pipeline_control import *


class ExecuteBundle(PipelineControl):
    def __init__(self,config):
        #config
        self.config = config

        xlen = config.xlen

        #functional units
        self.alu=alu.AluBundle(xlen)
        self.ls = loadstore.LoadStoreBundle(config)
        self.csr =csr.CSRUnitBundle(config)
        self.trapCSR = trap.TrapCSRBundle(config)
        self.csrUpdate = trap.TrapCSRUpdateBundle(config)

        # output
        self.result_o = Signal(intbv(0)[xlen:])
        self.reg_we_o = Signal(bool(0)) # Register File Write Enable
        self.rd_adr_o =  Signal(modbv(0)[5:]) # Target register

        self.jump_o = Signal(bool(0)) # Branch/jump
        self.jump_dest_o = Signal(intbv(0)[xlen:])

        self.invalid_opcode_fault = Signal(bool(0))

        # Optional downstream interlock and writeback forwarding. They remain
        # tied low in the legacy three-stage backend.
        self.hazard_i = Signal(bool(0))
        self.forward_we_i = Signal(bool(0))
        self.forward_rd_i = Signal(modbv(0)[5:])
        self.forward_data_i = Signal(modbv(0)[xlen:])

        PipelineControl.__init__(self)



    @block
    def SimpleExecute(self, decode, databus, debugport, clock, reset, debugRegisterBundle=None):
        """
        Simple execution Unit designed for single stage in-order execution
        decode : DecodeBundle class instance
        databus : DBusBundle instance
        debugport : DebugOutputBundle instance
        clock : clock
        reset : reset
        """

        assert self.config.loadstore_outstanding==1, "SimpleExecute requires config.loadstore_outstanding==1"
        assert not self.config.RVC, "Compressed ISA not implemented yet"

        busy = Signal(bool(0))
        valid = Signal(bool(0))
        rd_adr_reg = Signal(modbv(0)[5:])

        jump = Signal(bool(0))
        jump_r =  Signal(bool(0))
        jump_dest =  Signal(intbv(0)[self.config.xlen:])
        jump_dest_r = Signal(intbv(0)[self.config.xlen:])
        jump_busy = Signal(bool(0)) # Only used when not config.jump_bypass

        load_pending = Signal(bool(0))
        shift_pending = Signal(bool(0))
        pipelined_shifter = self.config.shifter_mode == "pipelined"
        jump_we = Signal(bool(0)) # rd write enable on jal/jalr
        debug_redirect_kill = Signal(bool(0))
        debug_ebreak_enable = Signal(bool(0))

        alu_inst = self.alu.alu(clock,reset,self.config.shifter_mode )
        ls_inst = self.ls.LoadStoreUnit(databus,clock,reset)

        if self.config.enableDebugModule:
            csr_inst = self.csr.CSRUnit(
                self.trapCSR,self.csrUpdate,clock,reset,
                debugCSRBundle=decode.debugCSRBundle,
                debugCSRUpdateBundle=decode.debugCSRUpdateBundle,
                debugRegisterBundle=debugRegisterBundle)
        else:
            csr_inst = self.csr.CSRUnit(self.trapCSR,self.csrUpdate,clock,reset)

        p_inst = self.pipeline_instance(busy,valid)

        if self.config.enableDebugModule:
            debug_ebreak_enable = decode.debugCSRBundle.ebreakm

            @always_seq(clock.posedge, reset=reset)
            def debug_redirect_seq():
                debug_redirect_kill.next = debugRegisterBundle.dpc_jump


        @always_seq(clock.posedge,reset=reset)
        def seq():

            jump_busy.next = False

            if self.taken:
                load_pending.next = decode.load_cmd
                shift_pending.next = pipelined_shifter and decode.alu_cmd and \
                    (decode.funct3_o == a3.RV32_F3_SLL or \
                     decode.funct3_o == a3.RV32_F3_SRL_SRA)
            else:
                if self.ls.valid_o:
                    load_pending.next = False
                if self.alu.valid_o:
                    shift_pending.next = False

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

            op1 = decode.op1_o
            op2 = decode.op2_o
            if self.forward_we_i and self.forward_rd_i != 0:
                if decode.uses_rs1_o and decode.source_rs1_o == self.forward_rd_i:
                    op1 = self.forward_data_i
                if decode.uses_rs2_o and decode.source_rs2_o == self.forward_rd_i:
                    op2 = self.forward_data_i

            # ALU Input wirings
            self.alu.funct3_i.next = decode.funct3_o
            self.alu.funct7_6_i.next = decode.funct7_o[5]
            self.alu.op1_i.next = op1
            self.alu.op2_i.next = op2

            # LS Unit Input wirings
            self.ls.funct3_i.next = decode.funct3_o
            self.ls.op1_i.next = op1
            self.ls.op2_i.next = op2
            self.ls.displacement_i.next = decode.displacement_o
            self.ls.store_i.next = decode.store_cmd

            #csr Unit Input Wirings
            self.csr.csr_adr.next = decode.priv_funct_12
            self.csr.op1_i.next = op1
            self.csr.funct3_i.next = decode.funct3_o

            # Pipeline
            busy.next = self.alu.busy_o or self.ls.busy_o or self.csr.busy_o or jump_busy or self.hazard_i
            valid.next = self.alu.valid_o or self.ls.valid_o  or self.csr.valid_o  or jump_we

            if self.config.jump_bypass:
                if self.config.enableDebugModule:
                    decode.kill_i.next = (self.taken and jump) or debug_redirect_kill
                else:
                    decode.kill_i.next = self.taken and jump
            else:
                if self.config.enableDebugModule:
                    decode.kill_i.next = jump_busy or debug_redirect_kill
                else:
                    decode.kill_i.next = jump_busy


            # Functional Unit selection

            self.alu.en_i.next = decode.alu_cmd and self.taken
            self.ls.en_i.next = ( decode.store_cmd or decode.load_cmd ) and self.taken
            self.csr.en_i.next = decode.csr_cmd and self.taken

            # Debug Interface
            debugport.jump_exec.next = self.taken and ( decode.branch_cmd or decode.jump_cmd or decode.jumpr_cmd)
            debugport.jump.next = jump


        @always_comb
        def mux():
            # Output multiplexers

            if self.taken and jump_we:
                self.result_o.next = decode.next_ip_o
            # Decode may already hold the following instruction when a
            # multi-cycle unit completes. Use the class captured at issue for
            # loads and pipelined shifts; single-cycle ALU and CSR results can
            # use the current registered decode class.
            elif load_pending:
                self.result_o.next = self.ls.result_o
            elif shift_pending or decode.alu_cmd:
                self.result_o.next = self.alu.res_o
            elif decode.csr_cmd:
                self.result_o.next = self.csr.result_o
            else:
                self.result_o.next = 0

            self.reg_we_o.next =  self.alu.valid_o or self.ls.we_o  or self.csr.valid_o or jump_we

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
        def mcause_update():
            # mcause comb logic. Aware that actual update of the mcause csr is enabled
            # by  elf.csrUpdate.we_mcause.next

            self.csrUpdate.mcause_irq.next = 0

            if decode.priv_funct_12[0]:
                self.csrUpdate.mcause.next = 0x3 # EBRAK
            else:
                self.csrUpdate.mcause.next = 0xb #ECALL



        @always_comb
        def jump_comb():

            upper = self.config.xlen
            lower = self.config.ip_low

            self.invalid_opcode_fault.next = False
            jump.next = False
            jump_dest.next = 0
            jump_we.next = False


            self.csrUpdate.mstatus_trap_enter.next = False
            self.csrUpdate.mstatus_trap_exit.next = False
            self.csrUpdate.we_mcause.next = False
            self.csrUpdate.we_mtval.next = False

            self.csrUpdate.mtval.next = 0

            # csrUpdate.mepc can be hard wired to decode.mepc_o
            # bcasue trigger happens with csrUpdate.
            self.csrUpdate.mepc.next = decode.mepc_o[upper:lower]
            self.csrUpdate.we_mepc.next = False

            if self.config.enableDebugModule:
                decode.execute_ebreak_i.next = False

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
                elif decode.sys_cmd:
                    if debug_ebreak_enable and \
                       decode.priv_funct_12 == PrivFunct12.RV32_F12_EBREAK:
                        decode.execute_ebreak_i.next = True
                    elif decode.priv_funct_12==PrivFunct12.RV32_F12_EBREAK or  decode.priv_funct_12==PrivFunct12.RV32_F12_ECALL:
                        jump_dest.next[upper:lower] = self.trapCSR.mtvec
                        jump.next = True
                        self.csrUpdate.mstatus_trap_enter.next=True
                        self.csrUpdate.we_mcause.next=True
                        self.csrUpdate.we_mepc.next=True
                    elif decode.priv_funct_12==PrivFunct12.RV32_F12_ERET:
                        jump_dest.next[upper:lower] = self.trapCSR.mepc
                        jump.next = True
                        self.csrUpdate.mstatus_trap_exit.next=True
                    else:
                        self.invalid_opcode_fault.next = True

            #TODO: Implement other functional units


        return instances()

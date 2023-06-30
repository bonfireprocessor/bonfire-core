"""
RISC-V CSR Module
(c) 2023 The Bonfire Project
License: See LICENSE
"""
from __future__ import print_function

from myhdl import *
from rtl.pipeline_control import *

from rtl.instructions import  CSRAdr

from rtl.util import signed_resize


class CSRUnitBundle(PipelineControl):
    def __init__(self,config):
        self.config = config
        xlen = config.xlen
        self.xlen = xlen

        # Inputs
        self.funct3_i = Signal(modbv(0)[3:])
        self.op1_i = Signal(modbv(0)[xlen:])
        self.csr_adr = Signal(modbv(0)[12:])
        #self.op2_i = Signal(modbv(0)[xlen:])
        #self.rd_i = Signal(modbv(0)[5:])

        # Status register Inputs
        # mepc and mcause are managed in the execution unit
        self.mepc_i = Signal(modbv(0)[xlen:])
        self.mcause_i = Signal(modbv(0)[xlen:])
       

        # Outputs
        self.result_o = Signal(modbv(0)[xlen:])
        #self.rd_o = Signal(modbv(0)[5:])
        #self.we_o = Signal(bool(0))
        self.invalid_op_o = Signal(bool(0))

        # Status Register outputs

        self.mtvec_o = Signal(modbv(0)[xlen:2])
        

        self.mie_o =Signal(bool(0))
        self.mpie_o = Signal(bool(0))

        PipelineControl.__init__(self)


 
    @block
    def CSRUnit(self,clock,reset):
        
        # Pipeline control
        busy = Signal(bool(0))
        valid = Signal(bool(0))

        # Status Registers
        mtvec = Signal(modbv(0)[self.xlen:2])
        mie = Signal(bool(0))
        mpie = Signal(bool(0))

        csr_in = Signal(modbv(0)[self.xlen:])

        # Flags
        inv_op = Signal(bool(0))
        inv_reg = Signal(bool(0))


        p_inst = self.pipeline_instance(busy,valid)


        @always_comb
        def csr_op():
    
            op = self.funct3_i[2:0]
            inv_op.next = 0
            if op == 0b01:
                self.result_o.next = self.op1_i # CSRRW
            elif op == 0b10:
                self.result_o.next = csr_in | self.op1_i #CSRRS
            elif op == 0b11:
                self.result_o.next = csr_in & ~self.op1_i #CSRRC
            else:
                inv_op.next = 1


        @always_comb
        def csr_select():
            rw = self.csr_adr[12:10]
            priv = self.csr_adr[10:9]
            grp = self.csr_adr[8:6]
            reg = self.csr_adr[6:]

            csr_in.next = 0

            inv_reg.next = 0


            if priv == 0b11:
                if rw == 0b11: # Read Only Registers
                    if reg == CSRAdr.isa:
                        csr_in.next[self.xlen:self.xlen-1]=0b01                        
                    elif reg == CSRAdr.vendorid or reg == CSRAdr.archid or CSRAdr.hartid:
                        pass
                    elif reg == CSRAdr.impid:
                        csr_in.next = 0x8000 # Dummy Value
                    else:
                        inv_reg.next = 1
                elif rw == 0: # Read Write Registers
                    inv_reg.next = 1 # Not implemnted yet 
                else:
                    inv_reg.next = 1
            else:
                inv_reg.next = 1




        @always_comb
        def csr_out():
            if self.taken:
                invalid = inv_op or inv_reg
                self.invalid_op_o.next = invalid
                if not invalid:
                    valid.next = 1

        return instances()
        
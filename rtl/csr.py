"""
RISC-V CSR Module
(c) 2023 The Bonfire Project
License: See LICENSE
"""
from __future__ import print_function

from myhdl import *
from rtl.pipeline_control import *

from rtl.instructions import  CSRAdr
from rtl.trap import CSR_ReadViewBundle


class CSRUnitBundle(PipelineControl):
    def __init__(self,config):
        self.config = config
        xlen = config.xlen
        self.xlen = xlen

        # Inputs
        self.funct3_i = Signal(modbv(0)[3:])
        self.op1_i = Signal(modbv(0)[xlen:])
        self.csr_adr = Signal(modbv(0)[12:])



        #Pipeline Output
        self.result_o = Signal(modbv(0)[xlen:])
        self.invalid_op_o = Signal(bool(0))


        PipelineControl.__init__(self)


    @block
    def CSRUnit(self,trap_csrs, trap_csr_upate,clock,reset):

        # Pipeline control
        busy = Signal(bool(0))
        valid = Signal(bool(0))

        csr_in = Signal(modbv(0)[self.xlen:])
        csr_out = Signal(modbv(0)[self.xlen:])

        # Flags
        inv_op = Signal(bool(0))
        inv_reg = Signal(bool(0))


        csr_we = Signal(bool(0)) # Write Enable for CSRs
        csr_select_adr = Signal(modbv(0)[7:]) # Currently selected CSR

        # CSR Address parts
        rw = Signal(modbv(0)[2:])
        priv = Signal(modbv(0)[2:])
        reg = Signal(modbv(0)[7:])

        #Read Interface
        trap_csr_read_view = CSR_ReadViewBundle(self.config)



        p_inst = self.pipeline_instance(busy,valid)
        p_csr_write_inst = trap_csrs.csr_write(csr_we,csr_select_adr,csr_out,trap_csr_upate,clock,reset)
        p_csr_read_inst = trap_csr_read_view.csr_read(csr_select_adr,trap_csrs)


        @always_comb
        def csr_op_proc():

            op = self.funct3_i[2:0]
            inv_op.next = 0
            if op == 0b01:
                csr_out.next = self.op1_i # CSRRW
            elif op == 0b10:
                csr_out.next = csr_in | self.op1_i #CSRRS
            elif op == 0b11:
                csr_out.next = csr_in & ~self.op1_i #CSRRC
            else:
                inv_op.next = 1


        @always_comb
        def csr_fields_proc():
            rw.next = self.csr_adr[12:10]
            priv.next = self.csr_adr[10:8]
            #grp.next = self.csr_adr[8:6]
            reg.next  = self.csr_adr[7:]


        @always_comb
        def csr_select_proc():

            csr_in.next = 0
            inv_reg.next = False
            csr_we.next = False
            csr_select_adr.next = reg

            if priv == 0b11:
                if rw == 0b11: # Read Only Registers
                    if reg == CSRAdr.vendorid or reg == CSRAdr.archid or reg == CSRAdr.hartid:
                        pass
                    elif reg == CSRAdr.impid:
                        csr_in.next = 0x8000 # Dummy Value
                    else:
                        inv_reg.next = True
                elif rw == 0: # Read Write Registers
                    if reg == CSRAdr.isa:
                        csr_in.next[32:30]=0b01
                    elif trap_csr_read_view.valid: # If Valid Trap Reigster selected
                        csr_we.next = self.taken
                        csr_in.next = trap_csr_read_view.data
                    else:
                        inv_reg.next = True
                else:
                    inv_reg.next = True
            else:
                inv_reg.next = True

        @always_comb
        def csr_result_proc():
            valid.next = False
            if self.taken:
                invalid = inv_op or inv_reg
                self.invalid_op_o.next = invalid
                if not invalid:
                    valid.next = True
                    self.result_o.next = csr_in


        return instances()

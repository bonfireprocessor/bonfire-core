"""
RISC-V CSR Module
(c) 2023 The Bonfire Project
License: See LICENSE
"""
from __future__ import print_function

from myhdl import *
from rtl.pipeline_control import *

from rtl.instructions import  CSRAdr


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


    def expand_ip(self,ip):
        res = modbv(0)[self.xlen:]
        res[self.xlen:self.config.ip_low]=ip
        return res

 
    @block
    def CSRUnit(self,trap_csrs, clock,reset):
        
        # Pipeline control
        busy = Signal(bool(0))
        valid = Signal(bool(0))

        csr_in = Signal(modbv(0)[self.xlen:])
        csr_out = Signal(modbv(0)[self.xlen:])

        # Flags
        inv_op = Signal(bool(0))
        inv_reg = Signal(bool(0))

        # CSR write interface
        csr_we = Signal(bool(0)) # Write Enable for CSRs
        wr_adr = Signal(modbv(0)[7:])

        p_inst = self.pipeline_instance(busy,valid)
        p_csr_write_inst = trap_csrs.csr_write(csr_we,wr_adr,csr_out,clock,reset)


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
        def csr_select_proc():
            rw = self.csr_adr[12:10]
            priv = self.csr_adr[10:8]
            grp = self.csr_adr[8:6]
            reg = self.csr_adr[7:]

            csr_in.next = 0
            inv_reg.next = False
            csr_we.next = False
            wr_adr.next = reg
          
            if priv == 0b11:
                if rw == 0b11: # Read Only Registers                                            
                    if reg == CSRAdr.vendorid or reg == CSRAdr.archid or reg == CSRAdr.hartid:
                        pass
                    elif reg == CSRAdr.impid:
                        csr_in.next = 0x8000 # Dummy Value
                    else:
                        inv_reg.next = True
                elif rw == 0: # Read Write Registers
                    csr_we.next = True    
                    if reg == CSRAdr.isa:
                        csr_in.next[32:30]=0b01
                    elif reg == CSRAdr.tvec:
                        csr_in.next = self.expand_ip(trap_csrs.mtvec) 
                    elif reg == CSRAdr.scratch:
                        csr_in.next = trap_csrs.mscratch
                    elif reg == CSRAdr.epc:
                        csr_in.next = self.expand_ip(trap_csrs.mepc)  
                    elif reg == CSRAdr.cause:
                        csr_in.next = trap_csrs.mcause   
                    elif reg == CSRAdr.tval:
                        csr_in.next = trap_csrs.mtval                    
                    else:    
                        inv_reg.next = True
                        csr_we.next = False
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

        # @always_seq(clock.posedge,reset=reset)
        # def seq():
        #     if self.taken and csr_we:
        #         if wr_reg == CSRAdr.isa:
        #             pass # not implemented yet   
        #         elif wr_reg == CSRAdr.tvec:
        #             mtvec.next = csr_out[self.xlen:2]         
        #         elif wr_reg == CSRAdr.scratch:
        #             mscratch.next = csr_out
                                           
        return instances()
        
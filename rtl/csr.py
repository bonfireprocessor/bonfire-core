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
from rtl.debug import DebugCSRReadViewBundle


class CSRUnitBundle(PipelineControl):
    def __init__(self,config):
        self.config = config
        xlen = config.xlen
        self.xlen = xlen

        # Inputs
        self.funct3_i = Signal(modbv(0)[3:])
        self.op1_i = Signal(modbv(0)[xlen:])
        self.csr_adr = Signal(modbv(0)[12:])
        self.source_i = Signal(modbv(0)[5:])



        #Pipeline Output
        self.result_o = Signal(modbv(0)[xlen:])
        self.invalid_op_o = Signal(bool(0))


        PipelineControl.__init__(self)


    @block
    def CSRUnit(self,trap_csrs, trap_csr_upate,clock,reset, debugCSRBundle=None, debugCSRUpdateBundle=None, debugRegisterBundle=None):

        # Pipeline control
        busy = Signal(bool(0))
        valid = Signal(bool(0))

        csr_in = Signal(modbv(0)[self.xlen:])
        csr_out = Signal(modbv(0)[self.xlen:])

        # Flags
        inv_op = Signal(bool(0))
        inv_reg = Signal(bool(0))


        csr_we = Signal(bool(0)) # Write Enable for CSRs
        csr_select_adr = Signal(modbv(0)[8:]) # Currently selected CSR
        csr_write_requested = Signal(bool(0))

        mcycle = Signal(modbv(0)[64:])
        mcycle_low_we = Signal(bool(0))
        mcycle_high_we = Signal(bool(0))

        bonfirecfg = (
            (int(self.config.pipeline_length == 4) << 0)
            | (int(self.config.writeback_bypass) << 1)
            | (int(self.config.enableDebugModule) << 2)
            | (int(self.config.jump_predictor) << 3)
            | (int(self.config.mem_write_early_term) << 4)
        )

        # CSR Address parts
        rw = Signal(modbv(0)[2:])
        priv = Signal(modbv(0)[2:])
        reg = Signal(modbv(0)[8:])

        #Read Interface
        trap_csr_read_view = CSR_ReadViewBundle(self.config)
        if debugCSRBundle is not None:
            assert debugCSRUpdateBundle is not None, "debug CSR access requires debugCSRUpdateBundle"
            assert debugRegisterBundle is not None, "debug CSR access requires debugRegisterBundle"
            debug_csr_read_view = DebugCSRReadViewBundle(self.config)



        p_inst = self.pipeline_instance(busy,valid)
        p_csr_write_inst = trap_csrs.csr_write(csr_we,csr_select_adr,csr_out,trap_csr_upate,clock,reset)
        p_csr_read_inst = trap_csr_read_view.csr_read(csr_select_adr,trap_csrs)
        if debugCSRBundle is not None:
            p_debug_csr_write_inst = debugCSRBundle.csr_write(csr_we,csr_select_adr,csr_out,debugCSRUpdateBundle,debugRegisterBundle,clock,reset)
            p_debug_csr_read_inst = debug_csr_read_view.csr_read(csr_select_adr,debugCSRBundle,debugRegisterBundle)

        @always(clock.posedge)
        def mcycle_seq():
            if reset:
                mcycle.next = 0
            elif mcycle_low_we:
                mcycle.next = concat(mcycle[64:32], csr_out)
            elif mcycle_high_we:
                mcycle.next = concat(csr_out, mcycle[32:0])
            else:
                mcycle.next = mcycle + 1

        @always_comb
        def csr_op_proc():

            op = self.funct3_i[2:0]

            if op == 0b01:
                csr_out.next = self.op1_i # CSRRW
                inv_op.next = 0
            elif op == 0b10:
                csr_out.next = csr_in | self.op1_i #CSRRS
                inv_op.next = 0
            elif op == 0b11:
                csr_out.next = csr_in & ~self.op1_i #CSRRC
                inv_op.next = 0
            else:
                inv_op.next = 1
                csr_out.next = csr_in

            csr_write_requested.next = (
                op == 0b01
                or ((op == 0b10 or op == 0b11) and self.source_i != 0)
            )


        @always_comb
        def csr_fields_proc():
            rw.next = self.csr_adr[12:10]
            priv.next = self.csr_adr[10:8]
            #grp.next = self.csr_adr[8:6]
            reg.next  = self.csr_adr[8:]


        if debugCSRBundle is not None:
            @always_comb
            def csr_select_proc():

                csr_in.next = 0
                inv_reg.next = False
                csr_we.next = False
                mcycle_low_we.next = False
                mcycle_high_we.next = False
                csr_select_adr.next = reg

                if priv == 0b11:
                    if rw == 0b11: # Read Only Registers
                        if csr_write_requested:
                            inv_reg.next = True
                        elif reg == CSRAdr.vendorid or reg == CSRAdr.archid or reg == CSRAdr.hartid:
                            pass
                        elif reg == CSRAdr.impid:
                            csr_in.next = 0x8000 # Dummy Value
                        elif reg == CSRAdr.mbonfirecfg:
                            csr_in.next = bonfirecfg
                        else:
                            inv_reg.next = True
                    elif rw == 0: # Read Write Registers
                        if reg == CSRAdr.isa:
                            csr_in.next[32:30]=0b01
                        elif trap_csr_read_view.valid: # If Valid Trap Reigster selected
                            csr_we.next = self.taken and csr_write_requested
                            csr_in.next = trap_csr_read_view.data
                        elif debug_csr_read_view.valid:
                            csr_we.next = self.taken and csr_write_requested
                            csr_in.next = debug_csr_read_view.data
                        else:
                            inv_reg.next = True
                    elif rw == 0b10: # Machine counter registers
                        if reg == CSRAdr.mcycle:
                            csr_in.next = mcycle[32:0]
                            mcycle_low_we.next = self.taken and csr_write_requested
                        elif reg == CSRAdr.mcycleh:
                            csr_in.next = mcycle[64:32]
                            mcycle_high_we.next = self.taken and csr_write_requested
                        else:
                            inv_reg.next = True
                    elif debug_csr_read_view.valid:
                        csr_we.next = self.taken and csr_write_requested
                        csr_in.next = debug_csr_read_view.data
                    else:
                        inv_reg.next = True
                else:
                    inv_reg.next = True
        else:
            @always_comb
            def csr_select_proc():

                csr_in.next = 0
                inv_reg.next = False
                csr_we.next = False
                mcycle_low_we.next = False
                mcycle_high_we.next = False
                csr_select_adr.next = reg

                if priv == 0b11:
                    if rw == 0b11: # Read Only Registers
                        if csr_write_requested:
                            inv_reg.next = True
                        elif reg == CSRAdr.vendorid or reg == CSRAdr.archid or reg == CSRAdr.hartid:
                            pass
                        elif reg == CSRAdr.impid:
                            csr_in.next = 0x8000 # Dummy Value
                        elif reg == CSRAdr.mbonfirecfg:
                            csr_in.next = bonfirecfg
                        else:
                            inv_reg.next = True
                    elif rw == 0: # Read Write Registers
                        if reg == CSRAdr.isa:
                            csr_in.next[32:30]=0b01
                        elif trap_csr_read_view.valid: # If Valid Trap Reigster selected
                            csr_we.next = self.taken and csr_write_requested
                            csr_in.next = trap_csr_read_view.data
                        else:
                            inv_reg.next = True
                    elif rw == 0b10: # Machine counter registers
                        if reg == CSRAdr.mcycle:
                            csr_in.next = mcycle[32:0]
                            mcycle_low_we.next = self.taken and csr_write_requested
                        elif reg == CSRAdr.mcycleh:
                            csr_in.next = mcycle[64:32]
                            mcycle_high_we.next = self.taken and csr_write_requested
                        else:
                            inv_reg.next = True
                    else:
                        inv_reg.next = True
                else:
                    inv_reg.next = True

        @always_comb
        def csr_result_proc():
           
            invalid = (inv_op or inv_reg)
            self.invalid_op_o.next = invalid  and self.taken
            self.result_o.next = csr_in
            valid.next = not invalid  and self.taken

        return instances()

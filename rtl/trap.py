"""
RISC-V Trap/IRQ Handling Module
(c) 2023-2026 The Bonfire Project
License: See LICENSE
"""
from __future__ import print_function

from myhdl import *
from rtl.pipeline_control import *

from rtl.instructions import  CSRAdr


class TrapCSRUpdateBundle:
     def __init__(self,config):
        self.config = config
        self.xlen = config.xlen
        xlen = config.xlen

        #Status Registers
        self.mepc = Signal(modbv(0)[xlen:config.ip_low])
        self.mcause =  Signal(modbv(0,min=0,max=config.mcause_max))
        self.mcause_irq = Signal(bool(0))
        self.mtval = Signal(modbv(0)[xlen:])

        self.we_mepc=Signal(bool(0))
        self.we_mcause=Signal(bool(0))
        self.mstatus_trap_enter=Signal(bool(0))
        self.mstatus_trap_exit=Signal(bool(0))
        self.we_mtval=Signal(bool(0))
      

class TrapCSRBundle:
    def __init__(self,config):
        self.config = config
        self.xlen = config.xlen
        xlen = config.xlen

        #Status Registers
        self.mepc = Signal(modbv(0)[xlen:config.ip_low])
        self.mcause = Signal(modbv(0,min=0,max=config.mcause_max))
        self.mcause_irq = Signal(bool(0))
        self.mtvec = Signal(modbv(0)[self.xlen:config.ip_low])
        self.mscratch = Signal(modbv(0)[self.xlen:])
        self.mstatus_mie = Signal(bool(0))
        self.mstatus_mpie = Signal(bool(0))
        self.mie = Signal(modbv(0)[xlen:])
        self.mtval = Signal(modbv(0)[xlen:])


    @block
    def csr_write(self,we,adr,data,update,clock,reset):
        """
        we: bool Write Enable
        adr : [6:] CSR Adr
        data: [32:] Input Data to wrtie
        update: TrapCSRUpdateBundle
        clock: clock signal
        reset : reset signal
        """

        upper = self.config.xlen
        lower = self.config.ip_low

        @always(clock.posedge)
        def seq():

            if reset:
                self.mtvec.next = 0
                self.mscratch.next = 0
                self.mepc.next = 0
                self.mcause.next = 0
                self.mcause_irq.next = False
                self.mtval.next = 0
                self.mstatus_mie.next = False
                self.mstatus_mpie.next = False
                self.mie.next = 0

            elif we: # Write CSR Register because of CSR instruction
                if adr == CSRAdr.tvec:
                    self.mtvec.next = data[upper:lower]
                elif adr == CSRAdr.scratch:
                    self.mscratch.next = data
                elif adr == CSRAdr.cause:
                    self.mcause.next = data[6:0]
                    self.mcause_irq.next = data[31]
                elif adr == CSRAdr.epc:
                    self.mepc.next = data[upper:lower]
                elif adr == CSRAdr.tval:
                    self.mtval.next = data
                elif adr == CSRAdr.status:
                    self.mstatus_mie.next = data[3]
                    self.mstatus_mpie.next = data[7]
                elif adr == CSRAdr.ie:
                    self.mie.next = data & 0xffff0888
            else: # Update CSR register beacuse of trap/irq handliong
                if update.we_mcause:
                    self.mcause.next = update.mcause
                    self.mcause_irq.next = update.mcause_irq
                if update.we_mepc:
                    self.mepc.next = update.mepc
                if update.mstatus_trap_enter: # DIsable MIE and store in MPIE on trap
                    self.mstatus_mpie.next = self.mstatus_mie
                    self.mstatus_mie.next = False
                if update.mstatus_trap_exit:
                    self.mstatus_mie.next = self.mstatus_mpie
                    self.mstatus_mpie.next = True
                if update.we_mtval:
                    self.mtval.next = update.mtval
                    

        return instances()



class CSR_ReadViewBundle:
    def __init__(self,config):
        self.config=config
        self.xlen = config.xlen
        xlen=config.xlen

        self.valid = Signal(bool(0))
        self.data = Signal(modbv(0)[xlen:])


    @block
    def csr_read(self,reg,trap_csrs):

        upper = self.config.xlen
        lower = self.config.ip_low

        @always_comb
        def comb():
            self.valid.next = True
            self.data.next=0

            if reg == CSRAdr.tvec:
                self.data.next[upper:lower] = trap_csrs.mtvec
            elif reg == CSRAdr.ie:
                self.data.next = trap_csrs.mie
            elif reg == CSRAdr.scratch:
                self.data.next = trap_csrs.mscratch
            elif reg == CSRAdr.epc:
                self.data.next[upper:lower] = trap_csrs.mepc
            elif reg == CSRAdr.cause:
                self.data.next = trap_csrs.mcause
                self.data.next[31] = trap_csrs.mcause_irq
            elif reg == CSRAdr.tval:
                self.data.next = trap_csrs.mtval
            elif reg == CSRAdr.status:
                self.data.next[13:11]=0b11
                self.data.next[7]=trap_csrs.mstatus_mpie
                self.data.next[3]=trap_csrs.mstatus_mie
            elif reg == CSRAdr.ip:
                # Pending interrupt inputs are introduced in Plan 03.
                self.data.next = 0
            else:
                self.valid.next=False


        return instances()
    

# class TrapIRQBundle:
#     def __init__(self,config):
#         self.config = config
#         self.xlen = config.xlen
#         xlen = config.xlen

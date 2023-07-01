"""
RISC-V Trap/IRQ Handling Module
(c) 2023 The Bonfire Project
License: See LICENSE
"""
from __future__ import print_function

from myhdl import *
from rtl.pipeline_control import *

from rtl.instructions import  CSRAdr

class TrapCSRBundle:
    def __init__(self,config):
        self.config = config
        self.xlen = config.xlen
        xlen = config.xlen

        self.mepc = Signal(modbv(0)[xlen:config.ip_low])
        self.mcause = Signal(modbv(0)[xlen:])
        self.mtvec = Signal(modbv(0)[self.xlen:config.ip_low])
        self.mscratch = Signal(modbv(0)[self.xlen:])
        self.mie = Signal(bool(0))
        self.mpie = Signal(bool(0))
        self.mtval = Signal(modbv(0)[xlen:])


  

    @block
    def csr_write(self,we,adr,data,clock,reset):
        """
        we: bool Write Enable
        adr : [6:] CSR Adr
        data: [32:] Input Data to wrtie
        clock: clock signal
        reset : reset signal
        """
        @always(clock.posedge)
        def seq():
            if reset:
                self.mtvec.next = False
                self.mie.next = False
                self.mpie.next = False

            elif we:
                if adr == CSRAdr.tvec:
                    self.mtvec.next = data[self.xlen:2]
                elif adr == CSRAdr.scratch:
                    self.mscratch.next = data
                elif adr == CSRAdr.cause:
                    self.mcause.next = data
                elif adr == CSRAdr.epc:
                    self.mepc.next = data
                elif adr == CSRAdr.tval:
                    self.mtval.next = data

        return instances()
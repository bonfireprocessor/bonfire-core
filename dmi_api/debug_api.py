"""
RISC-V Debug Api
(c) 2023 The Bonfire Project
License: See LICENSE
"""
from __future__ import print_function

from myhdl import *

from rtl.debugModule import AbstractDebugTransportBundle, DMI


class DebugAPI:

    def halt(self,HartId=0):
        return False

    def resume(self,HartId=0):
        return False
    
    def ResetCore(self):
        return False
    


class DebugAPISim(DebugAPI):
    def __init__(self,dtm_bundle,clock):
        self.dtm_bundle = dtm_bundle
        self.clock=clock
        self.halted = False
        self.result = modbv(0)[32:]


    def dmi_read(self,adr):
        yield self.clock.posedge
        self.dtm_bundle.adr.next=adr
        self.dtm_bundle.we.next=False
        self.dtm_bundle.en.next=True
        self.dtm_bundle.dbo.next=0xdeadbeef
        yield self.clock.posedge
        yield self.clock.posedge
        self.result._val = self.dtm_bundle.dbo
        self.dtm_bundle.en.next=False
       
    

    def dmi_write(self,adr,data):
        yield self.clock.posedge
        self.dtm_bundle.adr.next=adr
        self.dtm_bundle.we.next=True
        self.dtm_bundle.en.next=True
        self.dtm_bundle.dbi.next=data
        yield self.clock.posedge
        self.dtm_bundle.en.next=False
        
    



    def check_halted(self,HartId=0):

       yield self.dmi_read(0x11)
       self.halted = self.dtm_bundle.dbo[8]

    
    def halt(self,HartId=0):

        yield self.check_halted()
        if not self.halted:
            c=modbv(0x80000000)[32:]
            yield self.dmi_write(0x10,c)
            while not self.halted:
                yield self.check_halted()

        return True

    def resume(self,HartId=0):
        yield self.check_halted()
        if self.halted:
            c=modbv(0)[32:]
            c[30]=True
            yield self.dmi_write(0x10,c)
            while self.halted:
                yield self.check_halted()

                
            
    def ResetCore(self):
         c=modbv(0)[32:]
         c[1]=True
         self.dmi_write(0x10,c)
         c[1]=False
         self.dmi_write(0x10,c)
        

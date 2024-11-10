"""
RISC-V Debug Api
(c) 2023 The Bonfire Project
License: See LICENSE
"""
from __future__ import print_function

from myhdl import *

from rtl.debugModule import AbstractDebugTransportBundle, DMI


class DebugAPI:

    def __not_implemented():
        raise Exception("Not Implemented")

    def cmd_result(self):
        return 0

    def halt(self,HartId=0):
        self.__not_implemented()

    def resume(self,HartId=0):
        self.__not_implemented()

    def ResetCore(self):
        self.__not_implemented()

    def dmi_read(self,adr):
        self.__not_implemented

    def dmi_write(self,adr,data):
        self.__not_implemented()

    def check_halted(self,HartId=0):
        self.__not_implemented()

    def yield_clock(self):
        print("Warning: DebugAPI.yield_clock called")
        pass

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


    def readReg(self,HartId=0,regno=0,postexec=False,transfer=True,AssertCmdErr=True):

            c=modbv(0)[32:]
            c[23:20]=2 # aarsize 32Bit
            c[15:0]=regno
            c[17]=transfer
            c[18]=postexec
            yield self.dmi_write(0x17,c)
            yield self.yield_clock()
            yield self.dmi_read(0x16) # abstracts

            # wait until busy is cleared
            while self.result[12]:
                yield self.dmi_read(0x16) # abstracts

            self.cmderr=self.result[11:8]
            if AssertCmdErr:
                assert self.cmderr==0,"readReg command failed"
            if self.cmderr==0:
                yield self.dmi_read(0x4) # read Data reg 0
        # Register value should now be self.result

    def readGPR(self,HartId=0,regno=1,postexec=False,transfer=True):
        yield self.readReg(HartId=HartId,regno=regno+0x1000,postexec=postexec,transfer=transfer)


    def writeReg(self,HartId=0,regno=0,value=0,postexec=False,transfer=True,AssertCmdErr=True):

        yield self.dmi_write(0x4,value) # data0 reg

        c=modbv(0)[32:]
        c[23:20]=2 # aarsize 32Bit
        c[15:0]=regno
        c[17]=transfer
        c[18]=postexec
        c[16]=True #Write
        yield self.dmi_write(0x17,c)
        yield self.yield_clock()
        yield self.dmi_read(0x16) # abstracts

        # wait until busy is cleared
        while self.result[12]:
            yield self.dmi_read(0x16) # abstracts

        self.cmderr=self.result[11:8]
        if AssertCmdErr:
            assert self.cmderr==0,"readReg command failed"
      


    def writeGPR(self,HartId=0,regno=1,value=0,postexec=False,transfer=True):
        yield self.writeReg(HartId=HartId,regno=regno+0x1000,value=value,postexec=postexec,transfer=transfer)


    def ResetCore(self):
         c=modbv(0)[32:]
         c[1]=True
         self.dmi_write(0x10,c)
         c[1]=False
         self.dmi_write(0x10,c)


    def readMemory(self,HartId=0,memadr=0,readbyte=False):
        # See RISC-V Debug Spec B.2.7.2, Read Memory using Progam Buffer
        yield self.dmi_write(0x20,( 0x00044403 if readbyte else 0x00042403))  #   lw s0,0(s0) or lbu s0,0(s0) 
        yield self.writeGPR(regno=8,value=memadr,postexec=True,transfer=True)
        yield self.readGPR(regno=8,transfer=True)

    


    
    def writeMemory(self,HartId=0,memadr=0,memvalue=0):
        # See RISC-V Debug Spec B.2.8.2, Read Memory using Progam Buffer
        yield self.dmi_write(0x20,0x00942023)  # sw	s1,0(s0)  
        yield self.writeGPR(regno=8,value=memadr,transfer=True)
        yield self.writeGPR(regno=9,value=memvalue,postexec=True,transfer=True)

    


class DebugAPISim(DebugAPI):
    def __init__(self,dtm_bundle,clock):
        self.dtm_bundle = dtm_bundle
        self.clock=clock
        self.halted = False
        self.result = modbv(0)[32:]
        self.cmderr=0


    def cmd_result(self):
        return self.result+0    

    def yield_clock(self):
        yield self.clock.posedge


    def dmi_read(self,adr):
        yield self.clock.posedge
        self.dtm_bundle.adr.next=adr
        self.dtm_bundle.we.next=False
        self.dtm_bundle.en.next=True
        #self.dtm_bundle.dbo.next=0xffffffff # Test pattern
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



   
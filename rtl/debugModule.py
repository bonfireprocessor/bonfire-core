"""
RISC-V Hardware Debug Module
(c) 2023 The Bonfire Project
License: See LICENSE
"""
from __future__ import print_function

from myhdl import *
from rtl.pipeline_control import *

t_debugHartState = enum('running','halted')

debugSpecVersion = 15 # consider setting this to 2

class DebugRegisterBundle:
     def __init__(self,config):
        self.config = config
        xlen = config.xlen
        self.xlen = xlen

        self.harState=Signal(t_debugHartState.running)

        self.haltreq=Signal(bool(0))
        self.resumereq=Signal(bool(0))
        self.hartreset=Signal(bool(0))

        assert config.numdata<=16, "maximum allowed debug Data Registers are 16"

        self.dataRegs=  [Signal(modbv(0)[xlen:]) for ii in range(0, config.numdata)]
        self.progbuf0 = Signal(modbv(0)[xlen:])


class AbstractDebugTransportBundle:
    def __init__(self,config):
        self.config = config
        xlen = config.xlen
        self.xlen = xlen

        self.adr=modbv(0,max=0x40) # DMI adrees register 
        self.en=Signal(bool(0))
        self.we=Signal(bool(0))
        self.dbi=Signal(modbv(0)[32:])
        self.dbo=Signal(modbv(0)[32:])




class DMI:
    def __init__(self,config):
        self.config = config
        xlen = config.xlen
        self.xlen = xlen


    @block
    def DMI_interface(self,dtm,debugRegs,clock):
        """
        dtm: DebugTransportBundle
        debugRegs: Debug RegisterBundle

        """

        @always(clock.posedge)
        def seq():
            dtm.dbo.next=0
            if dtm.en:
                if not dtm.we:
                    if dtm.adr==0x11: #dmstatus
                        dtm.dbo.next[22] = True # impbreak
                        dtm.dbo.next[17] = not debugRegs.resumereq #allresumeack
                        dtm.dbo.next[16] = not debugRegs.resumereq #anyresumeack
                        dtm.dbo.next[11] = debugRegs.hartState==t_debugHartState.running #allrunning
                        dtm.dbo.next[10] = debugRegs.hartState==t_debugHartState.running #anyrunning
                        dtm.dbo.next[9] = debugRegs.hartState==t_debugHartState.halted #allhalted
                        dtm.dbo.next[8] = debugRegs.hartState==t_debugHartState.halted #anyhalted
                        dtm.dbo.next[4:] = debugSpecVersion # version
                    elif dtm.adr==0x10: #dmcontrol
                        dtm.dbo.next[1] = debugRegs.hartreset # ndmreset
                        dtm.dbo.next[0] = True
                    elif dtm.adr==0x12: # hartinfo
                        dtm.dbo.next[24:20] = self.config.num_dscratch
                        dtm.dbo.next[16:12] = self.config.numdata
                    elif dtm.adr==0x20: #progbuf0
                        dtm.dbo.next = debugRegs.progbuf0
                    elif (dtm.adr>=0x04) and (dtm.adr<=0x04+self.config.numdata-1): # data0 to data 0x11
                        dtm.dbo.next = debugRegs.dataRegs[dtm.adr-0x04]
                else: # Write
                    if dtm.adr==0x10:
                        haltreq = debugRegs.haltreq.next or dtm.dbi[31] # haltreq
                        debugRegs.haltreq.next = haltreq
                        debugRegs.resumereq.next = haltreq and dtm.dbi[30] #resumereq
                        debugRegs.hartReset.next = dtm.dbi[1] # ndmreset

        return instances()
                        
















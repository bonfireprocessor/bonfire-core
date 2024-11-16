"""
RISC-V Hardware Debug Module
(c) 2023 The Bonfire Project
License: See LICENSE
"""
from __future__ import print_function

from myhdl import *
from rtl.pipeline_control import *
from rtl.instructions import CSRAdr

t_debugHartState = enum('running','halted')
t_abstractCommandType = enum('access_reg','quick_access')
t_abstractCommandState  = enum('none','regvaild','taken','failed','exec','wait_retire')

debugSpecVersion = 15 # consider setting this to 2
csr_depc = 0x7b1

class DebugRegisterBundle:
     def __init__(self,config):
        self.config = config
        xlen = config.xlen
        self.xlen = xlen

        self.hartState=Signal(t_debugHartState.running)

        # Signals from DMI to debug core, written by DMI
        self.haltreq=Signal(bool(0))
        self.resumereq=Signal(bool(0))
        self.hartReset=Signal(bool(0))
        self.abstractCommandNew = Signal(bool(0))

        #Abstract Command access register fields written by DMI
        self.commandType = Signal(t_abstractCommandType.access_reg)
        self.aarsize = Signal(modbv(0))[2:]
        self.aarpostincrement = Signal(bool(0))
        self.postexec = Signal(bool(0))
        self.transfer = Signal(bool(0))
        self.write = Signal(bool(0))
        self.regno = Signal(modbv(0,max=32))
        self.cmderr = Signal(modbv(0)[3:])
        self.dpcAccess = Signal(bool(0))

        #written by DMI
        self.dataRegs = [Signal(modbv(0)[xlen:]) for ii in range(0, config.numdata)]
        self.progbuf0 = Signal(modbv(0)[xlen:])



        # Abtstract Command exeuction state, written by debug core
        self.abstractCommandState = Signal(t_abstractCommandState.none)
        self.abstractCommandResult =  Signal(modbv(0)[xlen:])

        # Ack Signal for halt or resume request, written by debug core 
        self.reqAck=Signal(bool(0)) 


        assert config.numdata<=16, "maximum allowed debug Data Registers are 16"

    
    
        #Debug CSRs, written by debug core
        self.dpc = Signal(modbv(0)[self.config.xlen:self.config.ip_low])
        #helpers
        self.dpc_jump=Signal(bool(0))


class AbstractDebugTransportBundle:
    def __init__(self,config):
        self.config = config
        xlen = config.xlen
        self.xlen = xlen

        self.adr=Signal(modbv(0,max=0x40))# DMI adrees register
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
            
            if debugRegs.reqAck:
                debugRegs.haltreq.next = False
                debugRegs.resumereq.next = False


            # Abstract Command exeuction management
            if debugRegs.abstractCommandState == t_abstractCommandState.regvaild:
                debugRegs.dataRegs[0].next = debugRegs.abstractCommandResult
            elif debugRegs.abstractCommandState == t_abstractCommandState.taken:
                debugRegs.abstractCommandNew.next = False

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
                        dtm.dbo.next[1] = debugRegs.hartReset # ndmreset
                        dtm.dbo.next[0] = True
                    elif dtm.adr==0x12: # hartinfo
                        dtm.dbo.next[24:20] = self.config.num_dscratch
                        dtm.dbo.next[16:12] = self.config.numdata
                    elif dtm.adr==0x20: #progbuf0
                        dtm.dbo.next = debugRegs.progbuf0
                    elif (dtm.adr>=0x04) and (dtm.adr<=0x04+self.config.numdata-1): # data0 to data 0x11
                        dtm.dbo.next = debugRegs.dataRegs[dtm.adr-0x04]
                    elif dtm.adr==0x16: #abstractcs
                        dtm.dbo.next[29:24] = 1 #progbufsize
                        dtm.dbo.next[12] = debugRegs.abstractCommandState != t_abstractCommandState.none # busy
                        dtm.dbo.next[11:8] = debugRegs.cmderr # cmderr
                        dtm.dbo.next[4:] = self.config.numdata # datacount

                else: # Write
                    if dtm.adr==0x10:
                        debugRegs.haltreq.next = debugRegs.hartState==t_debugHartState.running and dtm.dbi[31]
                        debugRegs.resumereq.next = debugRegs.hartState==t_debugHartState.halted and dtm.dbi[30]
                        debugRegs.hartReset.next = dtm.dbi[1] # ndmreset
                    elif (dtm.adr>=0x04) and (dtm.adr<=0x04+self.config.numdata-1): # data0 to data 0x11
                        debugRegs.dataRegs[dtm.adr-0x04].next = dtm.dbi    
                    elif dtm.adr==0x16: #abstractcs
                        debugRegs.cmderr.next =   debugRegs.cmderr &  ~dtm.dbi[11:8]  # clear cmderr bits with writing 1 to them
                    elif dtm.adr==0x17: # abstract command
                        if debugRegs.cmderr == 0: # dont start any new command as long cmderr is not cleared
                            if debugRegs.abstractCommandState != t_abstractCommandState.none:
                                debugRegs.cmderr.next = 1 # busy
                            if debugRegs.hartState==t_debugHartState.running:
                                debugRegs.cmderr.next = 4
                            elif dtm.dbi[32:24]==0:
                                debugRegs.commandType.next = t_abstractCommandType.access_reg
                                debugRegs.aarsize.next = dtm.dbi[23:20]
                                debugRegs.aarpostincrement.next = dtm.dbi[19]
                                debugRegs.postexec.next = dtm.dbi[18]
                                transfer = dtm.dbi[17]
                                debugRegs.transfer.next = transfer
                                debugRegs.write.next = dtm.dbi[16]
                                debugRegs.regno.next = dtm.dbi[5:0]
                                dpcAccess =  dtm.dbi[16:0] == (0x700 | CSRAdr.dpc)
                                debugRegs.dpcAccess.next = dpcAccess
                              
                                if dtm.dbi[16:5]==0x80 or dpcAccess or not transfer: # When Transfer is not set register number do not care
                                    debugRegs.abstractCommandNew.next = True
                                else:
                                    debugRegs.cmderr.next = 2 # not supported
                            # elif dtm.dbi[32:24]==1:
                            #     debugRegs.commandType.next = t_abstractCommandType.quick_access
                            #     debugRegs.abstractCommandState.next=t_abstractCommandState.new
                            else:
                                debugRegs.cmderr.next = 2 # not supported
                    elif dtm.adr==0x20: #progbuf0
                        debugRegs.progbuf0.next = dtm.dbi

        return instances()

















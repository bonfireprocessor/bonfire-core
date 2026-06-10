"""
RISC-V Hardware Debug Module
(c) 2023 The Bonfire Project
License: See LICENSE
"""
from __future__ import print_function

from myhdl import *
from rtl.pipeline_control import *
from rtl.instructions import CSRAdr
from util.diagnostics import get_diagnostics

t_debugHartState = enum('running','halted')
t_abstractCommandType = enum('access_reg','quick_access')
# exec,exec2 serve as progbuf pc: exec excutes progbuf0 and exec2 executes progbuf1 when progbuf_size is 2. 
# When progbuf_size is 1, exec2 will not be used and progbuf0 will be executed in exec state.
t_abstractCommandState  = enum('none','regvalid','taken','failed','exec','exec2','wait_retire')

debugSpecVersion = 2 # RISC-V Debug Spec 0.13
csr_depc = 0x7b1
xdedebugver = 4 # RISC-V Debug Spec 0.13

class DebugCSRUpdateBundle:
    def __init__(self,config):
        self.config = config
        self.xlen = config.xlen
        xlen = config.xlen

        self.dpc = Signal(modbv(0)[xlen:config.ip_low])
        self.cause = Signal(modbv(0)[3:0])
        self.we_dpc = Signal(bool(0))
        self.we_cause = Signal(bool(0))


class DebugCSRBundle():
    def __init__(self,config):
        self.config = config
        self.xlen = config.xlen

         #used dcsrs bits
        self.ebreakm = Signal(bool(0)) #dcsr[15]
        self.cause = Signal(modbv(0)[3:0]) #dcsr[8..6]
        self.step = Signal(bool(0)) #dcsr[2] single step mode

    @block
    def csr_write(self,we,adr,data,update,debugRegs,clock,reset):
        """
        we: bool Write Enable
        adr : [8:] CSR Adr
        data: [32:] Input data to write
        update: DebugCSRUpdateBundle
        debugRegs: DebugRegisterBundle
        clock: clock signal
        reset : reset signal
        """

        upper = self.config.xlen
        lower = self.config.ip_low

        @always(clock.posedge)
        def seq():
            if reset:
                self.ebreakm.next = False
                self.cause.next = 0
                self.step.next = False
                debugRegs.dpc.next = 0

            elif we:
                if adr == CSRAdr.dcsr:
                    self.ebreakm.next = data[15]
                    self.step.next = data[2]
                elif adr == CSRAdr.dpc:
                    debugRegs.dpc.next = data[upper:lower]
            else:
                if update.we_cause:
                    self.cause.next = update.cause
                if update.we_dpc:
                    debugRegs.dpc.next = update.dpc

        return instances()


class DebugCSRReadViewBundle:
    def __init__(self,config):
        self.config=config
        self.xlen = config.xlen
        xlen=config.xlen

        self.valid = Signal(bool(0))
        self.data = Signal(modbv(0)[xlen:])

    @block
    def csr_read(self,reg,debugCSRs,debugRegs):

        upper = self.config.xlen
        lower = self.config.ip_low

        @always_comb
        def comb():
            self.valid.next = True
            self.data.next = 0

            if reg == CSRAdr.dcsr:
                self.data.next[32:28] = xdedebugver
                self.data.next[15] = debugCSRs.ebreakm
                self.data.next[9:6] = debugCSRs.cause
                self.data.next[2] = debugCSRs.step
                self.data.next[2:0] = 3
            elif reg == CSRAdr.dpc:
                self.data.next[upper:lower] = debugRegs.dpc
            else:
                self.valid.next = False

        return instances()

class DebugRegisterBundle:
     def __init__(self,config):
        self.config = config
        xlen = config.xlen
        self.xlen = xlen

        assert self.config.progbuf_size in range(1,3), "progbuf_size must be 1 or 2"
        get_diagnostics().detail("DebugRegisterBundle: xlen={} ip_low={} numdata={} progbuf_size={} dmi_adr_width={}".format(
            config.xlen,
            config.ip_low,
            config.numdata,
            config.progbuf_size,
            config.dmi_adr_width,
        ))

        self.hartState=Signal(t_debugHartState.running)

        # Signals from DMI to debug core, written by DMI
        self.haltreq=Signal(bool(0))
        self.resumereq=Signal(bool(0))
        self.hartReset=Signal(bool(0))
        self.abstractCommandNew = Signal(bool(0))

        #Abstract Command access register fields written by DMI
        self.commandType = Signal(t_abstractCommandType.access_reg)
        self.aarsize = Signal(modbv(0)[3:])
        self.aarpostincrement = Signal(bool(0))
        self.postexec = Signal(bool(0))
        self.transfer = Signal(bool(0))
        self.write = Signal(bool(0))
        self.regno = Signal(modbv(0)[5:])
        self.cmderr = Signal(modbv(0)[3:])

        #written by DMI
        self.dataRegs = [Signal(modbv(0)[xlen:]) for ii in range(0, config.numdata)]
        self.progbuf0 = Signal(modbv(0)[xlen:])
        self.progbuf1 =  Signal(modbv(0)[xlen:]) # will not be used when progbuf_size==1
        # abstractauto controls whether accesses to dataN/progbufN also launch
        # the currently configured abstract command. OpenOCD uses this for
        # repeated memory reads through data0 without rewriting command.
        self.abstractAutoData = Signal(modbv(0)[config.numdata:])
        self.abstractAutoProgbuf = Signal(modbv(0)[config.progbuf_size:])



        # Abtstract Command exeuction state, written by debug core
        self.abstractCommandState = Signal(t_abstractCommandState.none)
        self.abstractCommandResult =  Signal(modbv(0)[xlen:])

        # Ack Signal for halt or resume request, written by debug core 
        self.reqAck=Signal(bool(0)) 

        # resumeack bit, used for dmstatus all/any resumeack
        self.resumeack = Signal(bool(0))

        # Internal core-to-debug signal. It marks that the currently accepted
        # pipeline instruction reached the execute result/commit point.
        self.instr_retired = Signal(bool(0))
        self.instr_retire_dpc = Signal(modbv(0)[self.config.xlen:self.config.ip_low])


        assert config.numdata<=16, "maximum allowed debug Data Registers are 16"

    
        #dpc, written by debug core
        self.dpc = Signal(modbv(0)[self.config.xlen:self.config.ip_low])
       

        #helpers
        self.dpc_jump=Signal(bool(0))


class AbstractDebugTransportBundle:
    def __init__(self,config):
        self.config = config
        xlen = config.xlen
        self.xlen = xlen

        self.adr=Signal(modbv(0)[config.dmi_adr_width:])# DMI adrees register
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
        get_diagnostics().detail("DMI_interface: numdata={} progbuf_size={} dmi_adr_width={}".format(
            self.config.numdata,
            self.config.progbuf_size,
            self.config.dmi_adr_width,
        ))

        @always(clock.posedge)
        def seq():
            
            if debugRegs.reqAck:
                if debugRegs.resumereq:
                    debugRegs.resumeack.next = True

                debugRegs.haltreq.next = False
                debugRegs.resumereq.next = False
                


            # Abstract Command exeuction management
            if debugRegs.abstractCommandState == t_abstractCommandState.regvalid:
                debugRegs.dataRegs[0].next = debugRegs.abstractCommandResult
            elif debugRegs.abstractCommandState == t_abstractCommandState.taken:
                debugRegs.abstractCommandNew.next = False

            dtm.dbo.next=0    
            if dtm.en:
                if not dtm.we:
                    if dtm.adr==0x11: #dmstatus
                        dtm.dbo.next[22] = True # impbreak
                        dtm.dbo.next[17] = debugRegs.resumeack #allresumeack
                        dtm.dbo.next[16] = debugRegs.resumeack #anyresumeack
                        dtm.dbo.next[11] = debugRegs.hartState==t_debugHartState.running #allrunning
                        dtm.dbo.next[10] = debugRegs.hartState==t_debugHartState.running #anyrunning
                        dtm.dbo.next[9] = debugRegs.hartState==t_debugHartState.halted #allhalted
                        dtm.dbo.next[8] = debugRegs.hartState==t_debugHartState.halted #anyhalted
                        dtm.dbo.next[7] = True  # authenticated
                        dtm.dbo.next[4:] = debugSpecVersion # version
                    elif dtm.adr==0x10: #dmcontrol
                        dtm.dbo.next[1] = debugRegs.hartReset # ndmreset
                        dtm.dbo.next[0] = True
                    elif dtm.adr==0x12: # hartinfo
                        dtm.dbo.next[24:20] = self.config.num_dscratch
                        dtm.dbo.next[16:12] = self.config.numdata
                    elif dtm.adr==0x18: #abstractauto
                        dtm.dbo.next[16+self.config.progbuf_size:16] = debugRegs.abstractAutoProgbuf
                        dtm.dbo.next[self.config.numdata:] = debugRegs.abstractAutoData
                    elif dtm.adr==0x20: #progbuf0
                        dtm.dbo.next = debugRegs.progbuf0
                        # autoexecprogbuf0: complete the register access and
                        # request the last abstract command again.
                        if debugRegs.abstractAutoProgbuf[0] and debugRegs.cmderr == 0:
                            if debugRegs.abstractCommandState != t_abstractCommandState.none:
                                debugRegs.cmderr.next = 1 # busy
                            elif debugRegs.hartState==t_debugHartState.running:
                                debugRegs.cmderr.next = 4
                            else:
                                debugRegs.abstractCommandNew.next = True
                    elif self.config.progbuf_size==2 and  dtm.adr==0x21: #progbuf1
                        dtm.dbo.next = debugRegs.progbuf1    
                        # autoexecprogbuf1 mirrors progbuf0 handling for a
                        # two-entry program buffer.
                        if debugRegs.abstractAutoProgbuf[1] and debugRegs.cmderr == 0:
                            if debugRegs.abstractCommandState != t_abstractCommandState.none:
                                debugRegs.cmderr.next = 1 # busy
                            elif debugRegs.hartState==t_debugHartState.running:
                                debugRegs.cmderr.next = 4
                            else:
                                debugRegs.abstractCommandNew.next = True
                    elif (dtm.adr>=0x04) and (dtm.adr<=0x04+self.config.numdata-1): # data0 to data 0x11
                        data_index = dtm.adr-0x04
                        dtm.dbo.next = debugRegs.dataRegs[data_index]
                        # autoexecdataN returns the current dataN value for this
                        # DMI read and schedules the next abstract command. This
                        # is why repeated data0 reads can stream memory words.
                        if debugRegs.abstractAutoData[data_index] and debugRegs.cmderr == 0:
                            if debugRegs.abstractCommandState != t_abstractCommandState.none:
                                debugRegs.cmderr.next = 1 # busy
                            elif debugRegs.hartState==t_debugHartState.running:
                                debugRegs.cmderr.next = 4
                            else:
                                debugRegs.abstractCommandNew.next = True
                    elif dtm.adr==0x16: #abstractcs
                        dtm.dbo.next[29:24] = self.config.progbuf_size # progbufsize
                        dtm.dbo.next[12] = debugRegs.abstractCommandState != t_abstractCommandState.none # busy
                        dtm.dbo.next[11:8] = debugRegs.cmderr # cmderr
                        dtm.dbo.next[4:] = self.config.numdata # datacount

                else: # Write
                    if dtm.adr==0x10:
                        debugRegs.haltreq.next = debugRegs.hartState==t_debugHartState.running and dtm.dbi[31]
                        if debugRegs.hartState==t_debugHartState.halted and dtm.dbi[30]:
                            debugRegs.resumereq.next = True
                            debugRegs.resumeack.next = False

                        debugRegs.hartReset.next = dtm.dbi[1] # ndmreset
                    elif (dtm.adr>=0x04) and (dtm.adr<=0x04+self.config.numdata-1): # data0 to data 0x11
                        data_index = dtm.adr-0x04
                        debugRegs.dataRegs[data_index].next = dtm.dbi
                        # Writes to dataN can also be autoexec triggers. The
                        # written value is visible to the command started here.
                        if debugRegs.abstractAutoData[data_index] and debugRegs.cmderr == 0:
                            if debugRegs.abstractCommandState != t_abstractCommandState.none:
                                debugRegs.cmderr.next = 1 # busy
                            elif debugRegs.hartState==t_debugHartState.running:
                                debugRegs.cmderr.next = 4
                            else:
                                debugRegs.abstractCommandNew.next = True
                    elif dtm.adr==0x16: #abstractcs
                        debugRegs.cmderr.next = debugRegs.cmderr & ~dtm.dbi[11:8]  # clear cmderr bits with writing 1 to them
                    elif dtm.adr==0x18: #abstractauto
                        # abstractauto[15:0] selects dataN autoexec triggers.
                        # abstractauto[31:16] selects progbufN autoexec triggers.
                        debugRegs.abstractAutoData.next = dtm.dbi[self.config.numdata:]
                        debugRegs.abstractAutoProgbuf.next = dtm.dbi[16+self.config.progbuf_size:16]
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
                               
                                if dtm.dbi[23:20]==2 and (dtm.dbi[16:5]==0x80 or not transfer): # Only support 32Bit transfers. When Transfer is not set, register number do not care
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
                        # Allow tools to update progbuf0 and immediately run the
                        # previously configured abstract command.
                        if debugRegs.abstractAutoProgbuf[0] and debugRegs.cmderr == 0:
                            if debugRegs.abstractCommandState != t_abstractCommandState.none:
                                debugRegs.cmderr.next = 1 # busy
                            elif debugRegs.hartState==t_debugHartState.running:
                                debugRegs.cmderr.next = 4
                            else:
                                debugRegs.abstractCommandNew.next = True
                    elif self.config.progbuf_size==2 and dtm.adr==0x21:
                        debugRegs.progbuf1.next = dtm.dbi
                        # Same autoexec behavior for the optional second
                        # progbuf entry.
                        if debugRegs.abstractAutoProgbuf[1] and debugRegs.cmderr == 0:
                            if debugRegs.abstractCommandState != t_abstractCommandState.none:
                                debugRegs.cmderr.next = 1 # busy
                            elif debugRegs.hartState==t_debugHartState.running:
                                debugRegs.cmderr.next = 4
                            else:
                                debugRegs.abstractCommandNew.next = True

        return instances()





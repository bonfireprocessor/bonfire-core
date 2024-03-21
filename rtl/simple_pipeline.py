"""
Simple 3 Stage Pipeline for bonfire_core
(c) 2019 The Bonfire Project
License: See LICENSE
"""


from myhdl import *

from rtl.decode import *
from rtl.execute import *
from rtl.regfile import *
from rtl.debugModule import *

from  rtl import config
def_config= config.BonfireConfig()

class FetchInputBundle:
     def __init__(self,config=def_config):
        self.config=config
        xlen=config.xlen

        self.en_i = Signal(bool(0)) # Fetch Data valid/ enable
        self.word_i = Signal(intbv(0)[xlen:]) # actual instruction to decode
        self.current_ip_i = Signal(modbv(0)[xlen:]) # ip (PC) of current instruction
        self.next_ip_i = Signal(modbv(0)[xlen:]) # ip (PC) of next instruction

class BackendOutputBundle:
    def __init__(self,config=def_config):
        self.config=config
        xlen=config.xlen

        self.jump_o =  Signal(bool(0))
        self.jump_dest_o =  Signal(intbv(0)[xlen:])
        self.busy_o = Signal(bool(0))



class SimpleBackend:
    def __init__(self,config=def_config):
        self.reg_portA = RFReadPort(xlen=config.xlen)
        self.reg_portB = RFReadPort(xlen=config.xlen)
        self.reg_writePort = RFWritePort(xlen=config.xlen)

        self.decode = DecodeBundle(xlen=config.xlen)
        self.execute =  ExecuteBundle(config)

        self.config=config


    @block
    def backend(self,fetchBundle, frontEnd, databus, clock, reset, out, debugport,debugRegisterBundle=None):

        regfile_inst = RegisterFile(clock,self.reg_portA,self.reg_portB,self.reg_writePort,self.config.xlen)
        decode_inst = self.decode.decoder(clock,reset,debugRegisterBundle=debugRegisterBundle)
        exec_inst = self.execute.SimpleExecute(self.decode, databus, debugport, clock,reset )

        d_e_inst = self.execute.connect(clock,reset,previous=self.decode)

        f_d_inst = self.decode.connect(clock,reset,previous=frontEnd)

        @always_comb
        def comb():
            # Wire up register file

            self.reg_portA.ra.next = self.decode.rs1_adr_o
            self.reg_portB.ra.next = self.decode.rs2_adr_o

            self.decode.rs1_data_i.next = self.reg_portA.rd
            self.decode.rs2_data_i.next = self.reg_portB.rd

            self.reg_writePort.wa.next = self.execute.rd_adr_o
            self.reg_writePort.we.next = self.execute.reg_we_o
            self.reg_writePort.wd.next = self.execute.result_o

            out.busy_o.next = self.decode.busy_o


            # Front end interface

            self.decode.word_i.next = fetchBundle.word_i
            self.decode.current_ip_i.next = fetchBundle.current_ip_i
            self.decode.next_ip_i.next  = fetchBundle.next_ip_i


        @always_comb
        def debugout():
            debugport.valid_o.next = self.execute.valid_o
            debugport.result_o.next = self.execute.result_o
            debugport.rd_adr_o.next = self.execute.rd_adr_o
            debugport.reg_we_o.next = self.execute.reg_we_o


        @always_comb
        def proc_out():
            out.jump_o.next = self.execute.jump_o
            out.jump_dest_o.next = self.execute.jump_dest_o





        return instances()


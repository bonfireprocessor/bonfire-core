"""
Simple 3 Stage Pioeline for bonfire_core 
(c) 2019 The Bonfire Project
License: See LICENSE
"""


from myhdl import *

from decode import *
from execute import *
from regfile import * 

import config
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

       
class DebugOutputBundle:
   def __init__(self,config=def_config):
       self.config=config
       xlen=config.xlen 

       self.result_o = Signal(intbv(0)[xlen:])
       self.rd_adr_o = Signal(intbv(0)[5:])
       self.reg_we_o = Signal(bool(0))


class SimpleBackend:
    def __init__(self,config=def_config):
        self.reg_portA = RFReadPort(xlen=config.xlen)
        self.reg_portB = RFReadPort(xlen=config.xlen)
        self.reg_writePort = RFWritePort(xlen=config.xlen)

        self.decode = DecodeBundle(xlen=config.xlen)
        self.execute =  ExecuteBundle(config)

        self.config=config 
        

    @block
    def backend(self,fetch,busy_o,databus, clock,reset,out,debugport ):

        regfile_inst = RegisterFile(clock,self.reg_portA,self.reg_portB,self.reg_writePort,self.config.xlen)
        decode_inst = self.decode.decoder(clock,reset)
        exec_inst = self.execute.SimpleExecute(self.decode, databus, clock,reset )

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

            busy_o.next = self.decode.busy_o 

            self.decode.stall_i.next = self.execute.busy_o 

            # Instruction fetch interface 

            self.decode.en_i.next = fetch.en_i
            self.decode.word_i.next = fetch.word_i
            self.decode.current_ip_i.next = fetch.current_ip_i
            self.decode.next_ip_i.next  = fetch.next_ip_i 


        @always_comb
        def debugout():
            debugport.result_o.next = self.execute.result_o
            debugport.rd_adr_o.next = self.execute.rd_adr_o
            debugport.reg_we_o.next = self.execute.reg_we_o


        @always_comb
        def proc_out():
            out.jump_o.next = self.execute.jump_o
            out.jump_dest_o.next = self.execute.jump_dest_o


        return instances()


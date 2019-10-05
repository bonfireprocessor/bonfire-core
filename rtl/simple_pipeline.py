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
        

class SimpleBackend:
    def __init__(self,config=def_config):
        self.reg_portA = RFReadPort(xlen=config.xlen)
        self.reg_portB = RFReadPort(xlen=config.xlen)
        self.reg_writePort = RFWritePort(xlen=config.xlen)

        self.decode = DecodeBundle(xlen=config.xlen)
        self.execute =  ExecuteBundle(config)

        self.config=config 
        

    @block
    def backend(self,fetch,busy_o,clock,reset):

        regfile_inst = RegisterFile(clock,self.reg_portA,self.reg_portB,self.reg_writePort,self.config.xlen)
        decode_inst = self.decode.decoder(clock,reset)
        exec_inst = self.execute.SimpleExecute(self.decode,clock,reset )

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
            self.decode.next_ip_i.next  = fetch.next_ip_i 
            

        return instances()


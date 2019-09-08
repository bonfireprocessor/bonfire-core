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


class SimplePipeline:
    def __init__(self,config=def_config):
        self.reg_portA = RFReadPort(xlen=config.xlen)
        self.reg_portB = RFReadPort(xlen=config.xlen)
        self.reg_writePort = RFWritePort(xlen=config.xlen)

        self.decode = DecodeBundle(xlen=config.xlen)
        self.execute =  ExecuteBundle(config)


    

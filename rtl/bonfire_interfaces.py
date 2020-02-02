"""
Bonfire Core  external Interface definitions
(c) 2019,2020 The Bonfire Project
License: See LICENSE
"""

from __future__ import print_function

from myhdl import *

class DbusBundle:
    """
    Simple Databus with enough features to be extended to Wishbone B4
    Can support pipelined mode, similar to Wishbone B4 pipelined mode
    """
    def __init__(self,config,readOnly=False):
        xlen=config.xlen

        self.xlen=xlen 
        
        self.en_o = Signal(bool(0))
       
        self.adr_o = Signal(modbv(0)[xlen:])  # Lower log2(xlen/8) bits will always be zero
        self.stall_i=Signal(bool(0)) # When True stall pipelining, a slave not supporting piplelining can keep stall True all the time
        self.ack_i=Signal(bool(0)) # True: Data are written or ready to read on the bus, terminates cycle
        self.error_i = Signal(bool(0)) # Signals a bus error (will be raised in place of ack_i)
        self.db_rd = Signal(modbv(0)[xlen:])
        if not readOnly:
            self.we_o = Signal(modbv(0)[xlen/8:]) # Byte wide write enable signals
            self.db_wr = Signal(modbv(0)[xlen:])


class ControlBundle:
    """
    Control lines of the processor core.
    E.g Interrupts
    Currently empty...
    """
    def __init__(self,config):
        pass

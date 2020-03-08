#!/usr/bin/env python
# Copyright (c) 2015 Angel Terrones (<angelterrones@gmail.com>)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from myhdl import * 
# from myhdl import always
# from myhdl import always_comb
# from myhdl import modbv
# from myhdl import instances 
# from myhdl import block


class RFReadPort:
    """
    Defines the RF's read IO port.

    :ivar ra: Read address
    :ivar rd: Read data
    """
    def __init__(self,xlen=32):
        """
        Initializes the IO ports.
        """
        self.ra = Signal(modbv(0)[5:])
        self.rd = Signal(modbv(0)[xlen:])


class RFWritePort:
    """
    Defines the RF's write IO port.

    :ivar wa: Write address
    :ivar we: Write enable
    :ivar wd: Write data
    """
    def __init__(self,xlen=32):
        """
        Initializes the IO ports.
        """
        self.wa = Signal(modbv(0)[5:])
        self.we = Signal(bool(False))
        self.wd = Signal(modbv(0)[xlen:])


@block 
def RegisterFile(clk,
                 portA,
                 portB,
                 writePort,
                 xlen=32):
    """
    The Register File (RF) module.
    32  registers, with the register 0 hardwired to zero.

    :param clk:       System clock
    :param portA:     IO bundle (read port)
    :param portB:     IO bundle (read port)
    :param writePort: IO bundle (write port)
    """
    registers = [Signal(modbv(0)[xlen:]) for ii in range(0, 32)]

    read_a = Signal(modbv(0)[xlen:])
    read_b = Signal(modbv(0)[xlen:])

    wdata_reg =  Signal(modbv(0)[xlen:])

    collision_a = Signal(bool(0))
    collision_b = Signal(bool(0))

    @always(clk.posedge)
    def read():
        """
        synchronous read operation. Rely on registers[0] to be always zero 
        """
        #read_a.next = registers[portA.ra]
        #read_b.next = registers[portB.ra] 
        if portA.ra != 0:
            read_a.next = registers[portA.ra]
        else:
            read_a.next = 0 

        if  portB.ra != 0:    
            read_b.next = registers[portB.ra] 
        else:
            read_b.next = 0      


    @always(clk.posedge)
    def write():
        """
        Synchronous write operation.

        If the write address is zero, do nothing.
        """
        if writePort.wa != 0 and writePort.we == 1:
            registers[writePort.wa].next = writePort.wd


            

    @always(clk.posedge)
    def collision():
        """
        Check if write occurs at the same address than read at same cycle 
        """
        if writePort.we:
            wdata_reg.next = writePort.wd 

        collision_a.next =  writePort.we and  writePort.wa == portA.ra and not portA.ra == 0
        collision_b.next =  writePort.we and  writePort.wa == portB.ra and not portB.ra == 0

    @always_comb
    def output():
        if collision_a:
            portA.rd.next = wdata_reg
        else:
            portA.rd.next = read_a

        if collision_b:
            portB.rd.next = wdata_reg
        else:
            portB.rd.next = read_b   


    return instances()
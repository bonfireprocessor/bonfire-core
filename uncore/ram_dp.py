"""
Bonfire Dual port RAM
(c) 2019,2020 The Bonfire Project
License: See LICENSE
"""

from __future__ import print_function

from myhdl import *


class RamPort32:
    def __init__(self,adrWidth=12,readOnly=False):
        self.readOnly = readOnly
        self.clock = Signal(bool(0))
        self.dbout = Signal(modbv(0)[32:])
        self.adrbus =  Signal(modbv(0)[adrWidth:])
        self.en = Signal(bool(0))
        if not readOnly:
            self.wren=Signal(modbv(0)[4:])
            self.dbin =  Signal(modbv(0)[32:])


def create_ram(ramfile,ramsize):
    ram = []
    adr = 0

    f=open(ramfile,"r")
    for line in f:
        i=int(line,16)
        ram.append(Signal(intbv(i)[32:]))
        adr += 1

    print("eof at adr:{}".format(hex(adr<<2)))    
    for i in range(adr,ramsize):
        ram.append(Signal(intbv(0)[32:]))

    print("Created ram with size {} words".format(len(ram)))
    return ram


@block
def port_instance(ram,port):

    @always(port.clock.posedge)
    def read():
        if port.en:
            port.dbout.next = ram[port.adrbus]

    if not port.readOnly:
        @always(port.clock.posedge)
        def write():
            if port.en:
                wd=modbv(0)[32:]
                wd[:] = ram[port.adrbus]
                for i in range(len(port.wren)):            
                    if port.wren[i]:
                        low = i * 8
                        high = low+8
                        wd[high:low] = port.dbin[high:low]
                ram[port.adrbus].next = wd

    return instances()

@block
def dbusToRamPort(dbus,port,clock,readOnly=False):

    ack_rd = Signal(bool(0))
    ack_wr = Signal(bool(0))

    we = Signal(bool(0))

    @always_comb
    def comb_rd():
        port.clock.next = clock
        port.en.next = dbus.en_o
        port.adrbus.next = dbus.adr_o[len(port.adrbus)+2:2]
        dbus.db_rd.next = port.dbout
        dbus.ack_i.next = ack_rd or ack_wr
        dbus.error_i.next = False
        dbus.stall_i.next = False
        

    if not readOnly:
        @always_comb
        def comb_wr():
            port.dbin.next = dbus.db_wr
            port.wren.next = dbus.we_o
            ack_wr.next = dbus.en_o and dbus.we_o
            we.next = dbus.we_o

    @always(clock.posedge)
    def seq():
        if ack_rd:
            ack_rd.next = False
        else:    
            ack_rd.next = dbus.en_o and not we

    return instances()


class DualportedRam:

    def __init__(self,initFileName, adrwidth=12):
        self.adrwidth=adrwidth
        self.ram = create_ram(initFileName,2**adrwidth)
       
        
    @block
    def ram_instance(self,porta,portb,clock):
        """
        porta: RamPort32 instance, port A
        portb: RamPort32 instance  port B
        """
        i_a = port_instance(self.ram,porta)
        i_b = port_instance(self.ram,portb)


        return instances()


    @block
    def ram_instance_dbus(self,db_a,db_b,clock):
        """
        db_a: dbus instance, port A
        db_b: dbus instance  port B
        
        """
        porta = RamPort32(self.adrwidth,db_a.readOnly)
        portb = RamPort32(self.adrwidth,db_b.readOnly)

        p1 = dbusToRamPort(db_a,porta,clock,db_a.readOnly)
        p1 = dbusToRamPort(db_b,portb,clock,db_b.readOnly)

        ram = self.ram_instance(porta,portb,clock)

        return instances()
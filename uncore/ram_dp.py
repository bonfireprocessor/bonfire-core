"""
Bonfire Dual port RAM
(c) 2019,2020 The Bonfire Project
License: See LICENSE
"""

from __future__ import print_function

from myhdl import *


class RamPort:
    def __init__(self,adrWidth=12,dataWidth=32,readOnly=False):
        assert dataWidth % 8 == 0, "RamPort dataWidth must be multiple of 8"
        self.readOnly = readOnly
        self.clock = Signal(bool(0))
        self.dbout = Signal(modbv(0)[dataWidth:])
        self.adrbus =  Signal(modbv(0)[adrWidth:])
        self.en = Signal(bool(0))

        if not readOnly:
            wren_length = dataWidth // 8
            self.wren=Signal(modbv(0)[wren_length:])
            self.dbin =  Signal(modbv(0)[dataWidth:])


# For backwards compatibilty
class RamPort32(RamPort):
    def __init__(self,adrWidth=12,readOnly=False):
        super().__init__(adrWidth=adrWidth,readOnly=readOnly)



def create_ram(ramfile,ramsize,dataWidth=32):
    ram = []
    adr = 0

    f=open(ramfile,"r")
    for line in f:
        i=int(line,16)
        ram.append(Signal(intbv(i)[dataWidth:]))
        adr += 1

    print("eof at adr:{}".format(hex(adr<<2)))
    for i in range(adr,ramsize):
        ram.append(Signal(intbv(0)[dataWidth:]))

    print("Created ram with size {} words, width={}".format(len(ram),dataWidth))
    return ram



@block
def port_instance(ram,port):
    """

    Connects a RAM Array to a port.
    In this ways it creates the actual BRAM instance

    Args:
        ram (List of intbv): RAM Array
        port (RamPort): Port to access the RAM Array


    """

    if port.readOnly:
        @always(port.clock.posedge)
        def ram_proc():
            if port.en:
                port.dbout.next = ram[port.adrbus]

    else:
        @always(port.clock.posedge)
        def ram_proc():
            if port.en:
                for i in range(len(port.wren)):
                    if port.wren[i]:
                        low = i * 8
                        high = low+8
                        ram[port.adrbus].next[high:low] = port.dbin[high:low]

                port.dbout.next = ram[port.adrbus]

    return instances()


@block
def dbusToRamPort(dbus,port,clock,readOnly=False):

    ack_rd = Signal(bool(0))    
    we = Signal(bool(0))

    @always_comb
    def comb_rd():
        port.clock.next = clock
        port.en.next = dbus.en_o
        port.adrbus.next = dbus.adr_o[len(port.adrbus)+2:2]
        dbus.db_rd.next = port.dbout
      
        dbus.error_i.next = False
        dbus.stall_i.next = False


    if not readOnly:
        @always_comb
        def comb_wr():
            port.dbin.next = dbus.db_wr
            port.wren.next = dbus.we_o
            t_we = dbus.we_o != 0           
            we.next = t_we
            dbus.ack_i.next = ack_rd or (t_we and dbus.en_o)
    
                  
        @always(clock.posedge)
        def seq():
            ack_rd.next = dbus.en_o and not we
    else:
        
                      
        @always(clock.posedge)
        def seq():
             dbus.ack_i.next = dbus.en_o

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

    # TODO: Check if obsolete !!!!
    @block
    def ram_instance_dbus(self,db_a,db_b,clock):
        """
        db_a: dbus instance, port A
        db_b: dbus instance  port B

        """
        porta = RamPort32(self.adrwidth,db_a.readOnly)
        portb = RamPort32(self.adrwidth,db_b.readOnly)

        p1 = dbusToRamPort(db_a,porta,clock,db_a.readOnly)
        p2 = dbusToRamPort(db_b,portb,clock,db_b.readOnly)

        ram = self.ram_instance(porta,portb,clock)

        return instances()


class DualportedRamLaned:


    def create_ram(self,ramfile,ramsize):

        self.ram = [ list() for i in range(4) ]

        adr = 0

        f=open(ramfile,"r")
        for line in f:
            v=int(line,16)
            temp=modbv(v)[32:0]
            self.ram[0].append(Signal(intbv(temp[8:0])[8:]))
            self.ram[1].append(Signal(intbv(temp[16:8])[8:]))
            self.ram[2].append(Signal(intbv(temp[24:16])[8:]))
            self.ram[3].append(Signal(intbv(temp[32:24])[8:]))

            adr += 1

        print("eof at adr:{}".format(hex(adr<<2)))
        for i in range(adr,ramsize):
            for k in range(0,4):
                self.ram[k].append(Signal(intbv(0)[8:]))


        print("Created  laned ram with size {} words".format(len(self.ram[0])))



    def __init__(self,initFileName, adrwidth=12):
        self.adrwidth=adrwidth
        self.create_ram(initFileName,2**adrwidth)


    @block
    def port_map(self,laneport,port,out,low,high,wr_index):

        @always_comb
        def map():
            laneport.clock.next = port.clock
            laneport.adrbus.next = port.adrbus
            laneport.en.next = port.en
            out.next = laneport.dbout


        if not port.readOnly:
            @always_comb
            def map_port_write():
                laneport.dbin.next = port.dbin[high:low]
                laneport.wren.next[0] = port.wren[wr_index]

        return instances()



    @block
    def ram_instance(self,porta,portb,clock):
        """

        porta: 32 Bit(!) RamPort instance, port A
        portb: 32 Bit(!)  RamPort instance  port B
        """
        lpa = [None for i in range (4)]
        lpb = [None for i in range (4)]

        ia = [None for i in range (4)]
        ib = [None for i in range (4)]

        i_map_a =  [None for i in range (4)]
        i_map_b =  [None for i in range (4)]
        
        out_a = [Signal(modbv(0)[8:]) for i  in range(4)]
        out_b = [Signal(modbv(0)[8:]) for i in range(4)]

        for i in range(4):
            low = i*8
            high =(i+1)*8

            # Create RAM Ports for every lane
            lpa[i] = RamPort(adrWidth=self.adrwidth,dataWidth=8,readOnly=porta.readOnly)
            lpb[i] = RamPort(adrWidth=self.adrwidth,dataWidth=8,readOnly=portb.readOnly)

            #Map 32 Bit Bus to the lanes
            i_map_a[i] = self.port_map(lpa[i],porta,out_a[i],low,high,i)
            i_map_b[i] = self.port_map(lpb[i],portb,out_b[i],low,high,i)

            # Wire them to the RAM lanes
            ia[i] = port_instance(self.ram[i],lpa[i])
            ib[i] = port_instance(self.ram[i],lpb[i])



        @always_comb
        def map_dbout():
            porta.dbout.next = concat(out_a[3],out_a[2],out_a[1],out_a[0])
            portb.dbout.next = concat(out_b[3],out_b[2],out_b[1],out_b[0])
            # for i in range(4):
            #     low = i*8
            #     high =(i+1)*8

            #     porta.dbout.next[high:low] = lpa[i].dbout
            #     portb.dbout.next[high:low] = lpb[i].dbout

        return instances()

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
    Signal names are from the master side
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


class Wishbone_master_bundle:
    """
    Wishbone master interface. Can be configured with the following parameters:
    adrHigh : Int, higest address bit, python style, "excluding" range, default 32
    adrLow  : Int, lowest address bit, default 2
    dataWidth : int, Databus width, default 32
    granularity : int, Port granularity, default 8, controls the creation of wb_sel signales
    b4_pipelined : generate stall_i signal
    bte_signals: generate cti_o and bte_o for burst support 


    """
    def __init__(self,adrHigh=32,adrLow=2,dataWidth=32,granularity=8, b4_pipelined=False,bte_signals=False,createErrorSignal=False):
        self.pipelined = b4_pipelined
        self.adrHigh = adrHigh
        self.adrLow = adrLow
        self.dataWidth=dataWidth
        self.granularity = granularity
        self.burstSupported = bte_signals
        self.errorSupported = createErrorSignal


        self.wbm_cyc_o = Signal(bool(0))
        self.wbm_stb_o = Signal(bool(0))
        self.wbm_ack_i = Signal(bool(0))
        if createErrorSignal:
            self.wbm_err_i = Signal(bool(0))

        self.wbm_we_o =  Signal(bool(0))
        self.wbm_adr_o = Signal(modbv(0)[adrHigh:adrLow])
        self.wbm_db_o = Signal(modbv(0)[dataWidth:])
        self.wbm_db_i =  Signal(modbv(0)[dataWidth:])
        if granularity != dataWidth:
            assert dataWidth % granularity == 0, "Wishbone bundle: invalid granularity, not a divider of datawidth"
            self.wbm_sel_o = Signal(modbv(0)[dataWidth/granularity:])
        if b4_signals:
            self.wbm_stall_i = Signal(bool(0))

        if bte_signals:
            self.wbm_cti_o = Signal(modbv(0)[3:])
            self.wbm_bte_o = Signal(modbv(0)[2:])
                
        

@block
def DbusToWishbone(dbus,wb,clock,reset):
    """
        Converts the internal DBusBundle to a Wishbone master
        Adapts automatically to the configuration of the Wishbone master
        Paremeters:

            dbus : DBusBundle
            wb : Wishbone Master
            clock : clock
            reset : reset Signal

    """
    # Sanity checks
    assert dbus.xlen == wb.dataWidth
    assert wb.adrHigh <= dbus.xlen

    stb_o = Signal(bool(0))
    cyc_o = Signal(bool(0))
    sel_o = Signal(modbv(0)[len(wb.wbm_sel_o):])
    we_o = Signal(bool(0))

    stall = Signal(bool(0))

    cyc_r = Signal(bool(0))

    @always_comb
    def cyc_proc():
        cyc_o.next = cyc_r or dbus.en_o

    @always_comb
    def wb_connect():
        # Outputs
        wb.wbm_cyc_o.next = cyc_o
        wb.wbm_sel_o.next = sel_o
        wb.wbm_stb_o.next = stb_o
        wbm.wbm_we_o.next = we_o
        wb.wbm_adr_o.next[wb.adrHigh:wb.adrLow] = dbus.adr_o[wb.adrHigh:wb.adrLow]
        wb.wbm_db_o.next = dbus.db_wr
        # Inputs
        dbus.ack_i.next = wb.wbm_ack_i
        dbus.db_rd.next = wb.wbm_db_i
        if wb.errorSupported:
            dbus.error_i.next = wb.wbm_err_i
        else:
            dbus.error_i.next = False

        dbus.stall_i.next = stall 


    if not dbus.readOnly:
        @always_comb
        def we_proc():
            if dbus.we_o:
                sel_o.next = dbus.we_o
                we_o.next = True
            else:
                sel_o.next = 0
                we_o.next = False 


    if wb.pipelined:
        @always_comb
        def wb_pipelined():
            stb_o.next = dbus.en_o
            stall.next = wb.wbm_stall_i
    else:
        # Convert Pipelined to non pipelined cycle, see WB4 spec chapter 5.2.1
        @always_comb
        def wb_standard():
            if cyc_o:
                stall.next = not wb.wbm_ack_i
            else:
                stall.next = False     

    @always_seq(clock.posedge,reset=reset)
    def seq():
        if wb.wbm_ack_i:
            cyc_r.next = False
        else:    
            cyc_r.next = dbus.en_o

    return instances()


     
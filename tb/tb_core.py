"""
Bonfire Core toplevel testbench
(c) 2019,2020 The Bonfire Project
License: See LICENSE
"""


from __future__ import print_function

from myhdl import *

from rtl import config, bonfire_core_top, bonfire_interfaces
from rtl.simple_pipeline import DebugOutputBundle

from ClkDriver import *
from sim_ram import *
from sim_monitor import *

import types
from disassemble import *
from math import log 



def create_ram(progfile,ramsize):
    ram = []
    adr = 0

    f=open(progfile,"r")
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
def tb(config=config.BonfireConfig(),hexFile="",elfFile="",sigFile="",ramsize=4096,verbose=False):

    ram = create_ram(hexFile,ramsize)

    ibus = bonfire_interfaces.DbusBundle(config,readOnly=True)
    dbus = bonfire_interfaces.DbusBundle(config)
    control = bonfire_interfaces.ControlBundle(config)
    debug = DebugOutputBundle(config)
    clock = Signal(bool(0))
    reset = ResetSignal(0, active=1, isasync=False)

    ram_dbus = bonfire_interfaces.DbusBundle(config)
    mon_dbus = bonfire_interfaces.DbusBundle(config)
    ram_sel_r = Signal(bool(0))

    mem = sim_ram()
    mem.setLatency(1)

    ibus_if = mem.ram_interface(ram,ibus,clock,reset,readOnly=True)
    dbus_if = mem.ram_interface(ram,ram_dbus,clock,reset)

    clk_driver= ClkDriver(clock)

    mon_i = monitor_instance(ram,mon_dbus,clock,sigFile=sigFile,elfFile=elfFile)

    core=bonfire_core_top.BonfireCoreTop(config)
    dut = core.createInstance(ibus,dbus,control,clock,reset,debug,config)



    @always_seq(clock.posedge,reset=reset)
    def slave_select():
        if ram_sel_r and ram_dbus.ack_i:
            ram_sel_r.next = False
        elif dbus.en_o and dbus.adr_o>>2 < ramsize:
            ram_sel_r.next = True 

    @always_comb
    def slave_connect():
        ram_sel =  dbus.adr_o>>2 < ramsize and dbus.en_o
        ram_dbus.en_o.next = ram_sel
        ram_dbus.we_o.next = dbus.we_o
        ram_dbus.adr_o.next = dbus.adr_o[log(ramsize,2)+2:]
        ram_dbus.db_wr.next = dbus.db_wr

        mon_dbus.en_o.next = not ram_sel and dbus.en_o
        mon_dbus.we_o.next = dbus.we_o
        mon_dbus.adr_o.next = dbus.adr_o
        mon_dbus.db_wr.next = dbus.db_wr

        if ram_sel or ram_sel_r:
            dbus.stall_i.next = ram_dbus.stall_i
            dbus.ack_i.next = ram_dbus.ack_i
            dbus.db_rd.next = ram_dbus.db_rd
        else:
            dbus.stall_i.next = mon_dbus.stall_i 
            dbus.ack_i.next = mon_dbus.ack_i
            dbus.db_rd.next = mon_dbus.db_rd

   
    @always_seq(clock.posedge,reset=reset)
    def sim_observe():

       
        d = core.backend.decode
        if core.backend.execute.taken:
            t_ip = d.debug_current_ip_o
            if verbose:
                print("@{}ns exc: {} : {} ".format(now(),t_ip,d.debug_word_o))
           
        
        inv = d.en_i and d.invalid_opcode and not d.kill_i
        assert not inv, "Invalid opcode @{}: pc:{} op:{} ".format(now(), d.current_ip_i,d.word_i)     
   
    return instances()


        
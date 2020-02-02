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

import types
from disassemble import *



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
        ram.append(Signal(intbv(0)))

    print("Created ram with size {} words".format(len(ram)))
    return ram


@block
def tb(config=config.BonfireConfig(),progfile="",ramsize=4096):

    ram = create_ram(progfile,ramsize)

    ibus = bonfire_interfaces.DbusBundle(config,readOnly=True)
    dbus = bonfire_interfaces.DbusBundle(config)
    control = bonfire_interfaces.ControlBundle(config)
    debug = DebugOutputBundle(config)
    clock = Signal(bool(0))
    reset = ResetSignal(0, active=1, isasync=False)

    mem = sim_ram()

    ibus_if = mem.ram_interface(ram,ibus,clock,reset,readOnly=True)
    dbus_if = mem.ram_interface(ram,dbus,clock,reset)

    clk_driver= ClkDriver(clock)

    core=bonfire_core_top.BonfireCoreTop(config)
    dut = core.createInstance(ibus,dbus,control,clock,reset,debug,config)


    @always_seq(clock.posedge,reset=reset)
    def sim_observe():

        backend=core.backend
        if backend.execute.taken:
            t_ip = backend.decode.debug_current_ip_o
            print("@{}ns exc: {} : {} ".format(now(),t_ip,backend.decode.debug_word_o))
            # assert code_ram[t_ip>>2]==backend.decode.debug_word_o, "pc vs ram content mismatch" 
            # assert backend.decode.next_ip_o == t_ip + 4, "next_ip vs. current_ip mismatch" 
            # current_ip_r.next = t_ip >> 2
   
    return instances()


        
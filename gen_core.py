"""
Bonfire Core toplevel generation 
(c) 2019,2020 The Bonfire Project
License: See LICENSE
"""

from __future__ import print_function

from myhdl import *

from rtl import config, bonfire_core_top, bonfire_interfaces
from rtl.simple_pipeline import DebugOutputBundle


config=config.BonfireConfig()
ibus = bonfire_interfaces.DbusBundle(config,readOnly=True)
dbus = bonfire_interfaces.DbusBundle(config)
control = bonfire_interfaces.ControlBundle(config)
debug = DebugOutputBundle(config)
clock = Signal(bool(0))
reset = ResetSignal(0, active=1, isasync=False)

inst = bonfire_core_top.BonfireCoreTop(ibus,dbus,control,clock,reset,debug,config)

inst.convert(hdl='VHDL',std_logic_ports=True,path='vhdl_gen', name="bonfire_core_top")
"""
Bonfire Core toplevel generation 
(c) 2019,2020 The Bonfire Project
License: See LICENSE
"""

from __future__ import print_function

from myhdl import *

from rtl import config, bonfire_interfaces
from rtl.simple_pipeline import DebugOutputBundle
from rtl.bonfire_core_top import BonfireCoreTop


config=config.BonfireConfig()
ibus = bonfire_interfaces.DbusBundle(config,readOnly=True)
dbus = bonfire_interfaces.DbusBundle(config)
control = bonfire_interfaces.ControlBundle(config)
debug = DebugOutputBundle(config)
clock = Signal(bool(0))
reset = ResetSignal(0, active=1, isasync=False)

core= BonfireCoreTop(config)
inst = core.createInstance(ibus,dbus,control,clock,reset,debug,config)

inst.convert(hdl='VHDL',std_logic_ports=True,path='vhdl_gen', name="bonfire_core_top")
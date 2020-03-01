"""
Very basic SoC
(c) 2019,2020 The Bonfire Project
License: See LICENSE
"""
from __future__ import print_function

from myhdl import *

from rtl import bonfire_core_top
from rtl import config
from rtl import bonfire_interfaces
from rtl.simple_pipeline import DebugOutputBundle

from ram_dp import *
from uncore.dbus_interconnect import *
from tb.sim_monitor import *

@block
def soc_instance(wb_master,db_master,clock,reset,hexfile,config=config.BonfireConfig()):
    """
    wb_master: Wishbone_master_bundle mapped at address 0x01000000
    db_master: DbusBundle mapped at address 0x100000000
    clock : cpu clock
    reset : reset signal
    hexfile : RAM initalization file
   
    """

    ibus = bonfire_interfaces.DbusBundle(config,readOnly=True)
    dbus = bonfire_interfaces.DbusBundle(config)
    control = bonfire_interfaces.ControlBundle(config)
    debug = DebugOutputBundle(config)

    db_slave1 = bonfire_interfaces.DbusBundle(config)
    db_slave2 = bonfire_interfaces.DbusBundle(config)
    
    ic_class= DbusInterConnects()
    ic = DbusInterConnects.Master3Slaves(dbus,db_slave1,db_slave2,db_master,clock,reset, \
        AdrMask(32,28,0),AdrMask(32,28,0x2),AdrMask(32,28,0x1))


    core=bonfire_core_top.BonfireCoreTop(config)
    core_i = core.createInstance(ibus,dbus,control,clock,reset,debug,config)

    wb_i = bonfire_interfaces.DbusToWishbone(db_slave2,wb_master,clock,reset)

    ram = DualportedRam(hexfile)
    ram_i = ram.ram_instance_dbus(ibus,db_slave1,clock)

    
    return instances()
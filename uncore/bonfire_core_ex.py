"""
Extended Bonfire Core toplevel
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
def bonfireCoreExtendedInterface(wb_master,db_master,bram_a,bram_b,clock,reset,
                                 config=config.BonfireConfig(),bram_adrWidth=12,
                                 wb_mask=AdrMask(32,28,0x2),
                                 db_mask=AdrMask(32,28,0x1),
                                 bram_mask=AdrMask(32,28,0)):
    """
    wb_master: Wishbone_master_bundle mapped at address 0x02000000
    db_master: DbusBundle mapped at address 0x100000000
    bram_a: Instruction RamPort32, should be read only, mapped at address 0
    bram_b: Data RamPort32 mapped at address 0
    clock : cpu clock
    reset : reset signal
    wb_mask : Address mask for Wishbone interface 
    db_mask : Address mask for native data bus interface 
    bram_mask : Address mask for Block RAM
    """

    ibus = bonfire_interfaces.DbusBundle(config,readOnly=True)
    dbus = bonfire_interfaces.DbusBundle(config)
    control = bonfire_interfaces.ControlBundle(config)
    debug = DebugOutputBundle(config)

    db_master_bram = bonfire_interfaces.DbusBundle(config) # Block RAM 
    db_master_wb = bonfire_interfaces.DbusBundle(config) # Wishbone DBUS
    
    ic_class= DbusInterConnects()
    ic = DbusInterConnects.Master3Slaves(dbus,db_master_bram,db_master_wb,db_master,clock,reset,
         bram_mask,wb_mask,db_mask)


    core=bonfire_core_top.BonfireCoreTop(config)
    core_i = core.createInstance(ibus,dbus,control,clock,reset,debug,config)

    wb_i = bonfire_interfaces.DbusToWishbone(db_master_wb,wb_master,clock,reset)

    p_a = dbusToRamPort(ibus,bram_a,clock,readOnly=True)
    p_b = dbusToRamPort(db_master_bram,bram_b,clock,readOnly=False)

    
    return instances()
"""
Extended Bonfire Core toplevel
(c) 2019,2020 The Bonfire Project
License: See LICENSE
"""
from __future__ import annotations, print_function

from typing import Any

from myhdl import *

from rtl import bonfire_core_top
from rtl import config
from rtl import bonfire_interfaces
from rtl.bonfire_interfaces import ControlBundle, DbusBundle, DebugOutputBundle, Wishbone_master_bundle
from rtl.config import BonfireConfig
from rtl.debug import DmiBundle
from rtl.type_aliases import BitSignal


from rtl.uncore.ram_dp import *
from rtl.uncore.dbus_interconnect import *
from tb.sim_monitor import *

@block
def bonfireCoreExtendedInterface(wb_master: Wishbone_master_bundle, db_master: DbusBundle,
                                 bram_a: RamPort32, bram_b: RamPort32,
                                 clock: BitSignal, reset: BitSignal,
                                 config: BonfireConfig = config.BonfireConfig(),
                                 wb_mask: AdrMask = AdrMask(32,28,0x2),
                                 db_mask: AdrMask = AdrMask(32,28,0x1),
                                 bram_mask: AdrMask = AdrMask(32,28,0),
                                 register_wishbone_dbus: bool = False,
                                 debugTransportBundle: DmiBundle | None = None) -> Any:
    """
    wb_master: Wishbone_master_bundle mapped at address 0x02000000
    db_master: DbusBundle mapped at address 0x100000000
    bram_a: Instruction RamPort32, should be read only
    bram_b: Data RamPort32 mapped
    clock : cpu clock
    reset : reset signal
    wb_mask : Address mask for Wishbone interface 
    db_mask : Address mask for native data bus interface 
    bram_mask : Address mask for Block RAM
    """

    ibus: DbusBundle = bonfire_interfaces.DbusBundle(config,readOnly=True)
    dbus: DbusBundle = bonfire_interfaces.DbusBundle(config)
    control: ControlBundle = bonfire_interfaces.ControlBundle(config)
    debug: DebugOutputBundle = bonfire_interfaces.DebugOutputBundle(config)

    db_master_bram: DbusBundle = bonfire_interfaces.DbusBundle(config) # Block RAM 
    db_master_wb: DbusBundle = bonfire_interfaces.DbusBundle(config) # Wishbone DBUS
    
    ic_class= DbusInterConnects()
    #ic = DbusInterConnects.Master3Slaves(dbus,db_master_bram,db_master_wb,db_master,clock,reset,
    #     bram_mask,wb_mask,db_mask)
    ic=DbusInterConnects.Master8Slaves(
        dbus, clock, reset,
        slave0=db_master_bram,
        slave1=db_master_wb,
        slave2=db_master,
        adrmask0=bram_mask,
        adrmask1=wb_mask,
        adrmask2=db_mask,
        register_slave1=register_wishbone_dbus)
    
    core=bonfire_core_top.BonfireCoreTop(config)
    core_i = core.createInstance(
        ibus,dbus,control,clock,reset,debug,config,
        debugTransportBundle=debugTransportBundle)

    wb_i = bonfire_interfaces.DbusToWishbone(db_master_wb,wb_master,clock,reset)

    p_a = dbusToRamPort(ibus,bram_a,clock,readOnly=True)
    p_b = dbusToRamPort(db_master_bram,bram_b,clock,readOnly=False)

    
    return instances()

from __future__ import print_function

from myhdl import *

from  uncore import bonfire_core_soc
from rtl import bonfire_interfaces,config
from tb.ClkDriver import *
from tb.sim_monitor import *

@block
def tb(config=config.BonfireConfig(),hexFile=""):

    clock = Signal(bool(0))
    reset = ResetSignal(0, active=1, isasync=False)
    
    dbus = bonfire_interfaces.DbusBundle(config)
    wb_master = bonfire_interfaces.Wishbone_master_bundle()


    clk_driver= ClkDriver(clock)
    mon_i = monitor_instance(None ,dbus,clock)

    soc_i = bonfire_core_soc.soc_instance(wb_master,dbus,clock,reset,hexFile,config)

    return instances()
    
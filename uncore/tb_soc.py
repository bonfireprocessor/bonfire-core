from __future__ import print_function

from myhdl import *

from  uncore import bonfire_core_soc,ram_dp
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
    bram_port_a = ram_dp.RamPort32(readOnly=True)
    bram_port_b = ram_dp.RamPort32()

    soc_i = bonfire_core_soc.soc_instance(wb_master,dbus,bram_port_a,bram_port_b,clock,reset,config=config)
    soc_i.convert(hdl='VHDL',std_logic_ports=True,path='vhdl_gen', name="bonfire_core_soc_top")

    ram = ram_dp.DualportedRam(hexFile)
    ram_i = ram.ram_instance(bram_port_a,bram_port_b,clock)
    
    return instances()
    
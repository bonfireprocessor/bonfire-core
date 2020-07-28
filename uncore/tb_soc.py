from __future__ import print_function

from myhdl import *

from  uncore import bonfire_core_ex,ram_dp
from rtl import bonfire_interfaces,config
from tb.ClkDriver import *
from tb.sim_monitor import *
from uncore.tb_wishbone_bfm import Wishbone_bfm

@block
def tb(config=config.BonfireConfig(),hexFile="",elfFile="",sigFile=""):

    clock = Signal(bool(0))
    reset = ResetSignal(0, active=1, isasync=False)
    
    dbus = bonfire_interfaces.DbusBundle(config)
    wb_master = bonfire_interfaces.Wishbone_master_bundle()
    wb_bfm = Wishbone_bfm()

    clk_driver= ClkDriver(clock,period=10)
   
    bram_port_a = ram_dp.RamPort32(readOnly=True)
    bram_port_b = ram_dp.RamPort32()

    soc_i = bonfire_core_ex.bonfireCoreExtendedInterface(wb_master,dbus,bram_port_a,bram_port_b,clock,reset,config=config)
   

    ram = ram_dp.DualportedRam(hexFile)
    ram_i = ram.ram_instance(bram_port_a,bram_port_b,clock)
    
    mon_i = monitor_instance(ram.ram ,dbus,clock,sigFile=sigFile,elfFile=elfFile)
    bfm_i = wb_bfm.Wishbone_check(wb_master,clock,reset)    

    return instances()
    
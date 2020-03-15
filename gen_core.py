"""
Bonfire Core toplevel generation 
(c) 2019,2020 The Bonfire Project
License: See LICENSE
"""

from __future__ import print_function
import getopt, sys 

from myhdl import *

from rtl import config, bonfire_interfaces
from rtl.simple_pipeline import DebugOutputBundle
from rtl.bonfire_core_top import BonfireCoreTop
from  uncore import bonfire_core_ex,ram_dp
from  uncore.dbus_interconnect import AdrMask



def gen_core(config,hdl,name,path):
    ibus = bonfire_interfaces.DbusBundle(config,readOnly=True)
    dbus = bonfire_interfaces.DbusBundle(config)
    control = bonfire_interfaces.ControlBundle(config)
    debug = DebugOutputBundle(config)
    clock = Signal(bool(0))
    reset = ResetSignal(0, active=1, isasync=False)

    core= BonfireCoreTop(config)
    inst = core.createInstance(ibus,dbus,control,clock,reset,debug,config)

    inst.convert(hdl=hdl,std_logic_ports=True,path=path, name=name)


def gen_extended_core(config,hdl,name,path,bram_adr_base=0,bramAdrWidth=12):
    clock = Signal(bool(0))
    reset = ResetSignal(0, active=1, isasync=False)
    
    dbus = bonfire_interfaces.DbusBundle(config)
    wb_master = bonfire_interfaces.Wishbone_master_bundle()

   
    bram_port_a = ram_dp.RamPort32(readOnly=True,adrWidth=bramAdrWidth)
    bram_port_b = ram_dp.RamPort32(adrWidth=bramAdrWidth)

    config.reset_address=bram_adr_base << 24
    soc_i = bonfire_core_ex.bonfireCoreExtendedInterface(wb_master,dbus,
            bram_port_a,bram_port_b,clock,reset,config=config,
            bram_mask=AdrMask(32,28,bram_adr_base))

    soc_i.convert(hdl=hdl,std_logic_ports=True,path=path, name=name)



try:
    opts, args = getopt.getopt(sys.argv[1:],"n" ,["hdl=","name=","extended","bram_base=","path=","bram_adr_width="])
except getopt.GetoptError as err:
    # print help information and exit:
    print(err)  # will print something like "option -a not recognized"
    sys.exit(2)

name_overide = ""
hdl = "VHDL"
extended = False
bram_base = 0x0
bram_adr_width = 12
gen_path = "vhdl_gen"

for o,a in opts:
    print(o,a)
    if o in ("-n","--name"):
        name_overide=a
  
    elif o == "--hdl":
        hdl=a
    elif o=="--bram_base":
        bram_base = int(a,0) 
    elif o=="--bram_adr_width":
        bram_adr_width = int(a,0)         
    elif o == "--extended":
        extended = True
    elif o == "--path":
        gen_path = a     
    
if not extended:
    config=config.BonfireConfig()
    if name_overide:
        n=name_overide
    else:
        n="bonfire_core_top"
    gen_core(config,hdl,n,path)        
else:
    config=config.BonfireConfig()
    if name_overide:
        n=name_overide
    else:
        n="bonfire_core_extended_top"

    gen_extended_core(config,hdl,n,gen_path,bram_adr_base=bram_base,bramAdrWidth=bram_adr_width) 
from __future__ import print_function
import getopt, sys

from soc import bonfire_core_soc



def gen_test():
    from rtl import config

    try:
        opts, args = getopt.getopt(sys.argv[1:],"n" ,["hdl=","name=","gentb",
                                   "bram_base=","path=","bram_adr_width=",
                                   "num_leds=","hexfile="])

    except getopt.GetoptError as err:
        # print help information and exit:
        print(err)  # will print something like "option -a not recognized"
        sys.exit(2)

    name_overide = ""
    hdl = "VHDL"
  
    bram_base = 0x0
    bram_adr_width = 12
    gen_path = "vhdl_gen"
    hexfile=""
    gentb = False

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
        elif o == "--path":
            gen_path = a
        elif o == "--hexfile":
            hexfile = a
        elif o == "--gentb":
            gentb = True    

    config=config.BonfireConfig()
    config.jump_bypass = False

    if name_overide:
        n=name_overide
    else:
        if gentb:
            n="bonfire_core_soc_tb"
        else:    
            n="bonfire_core_soc_top"


    Soc = bonfire_core_soc.BonfireCoreSoC(config,hexfile=hexfile)
    Soc.gen_soc(hdl,n,gen_path,gentb=gentb)

gen_test()
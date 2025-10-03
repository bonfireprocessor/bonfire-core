from __future__ import print_function
import getopt, sys

from soc import bonfire_core_soc


def get(parameters,key,default):

    try:
        return parameters[key]
    except KeyError:
        return default



def fusesoc_gen():
    import os
    import yaml
    from rtl import config

    CORE_TEMPLATE = """CAPI=2:
name: {vlnv}

filesets:
    rtl:
        file_type: {filetype}
        files: [ {files} ]
targets:
    default:
        filesets: [ rtl ]

"""

    print(sys.argv[1])
    try:
        with open(sys.argv[1], mode='r') as f:
            p=yaml.load(f, Loader=yaml.Loader)
            print(yaml.dump(p))
            files_root=p["files_root"]
            parameters=p["parameters"]
            print("Generating into: {}".format(os.getcwd()))


            hdl = get(parameters,"language","VHDL")
            name= get(parameters,"entity_name","bonfire_core_soc_top")
            vlnv = p["vlnv"]
            os.system("rm -f *.vhd *.v *.core")

            extended = True
            soc_config = {
                "bramAdrWidth": get(parameters, "bram_adr_width", 11),
                "LanedMemory": get(parameters, "laned_memory", True),
                "numLeds": get(parameters, "num_leds", 4),
                "ledActiveLow": get(parameters, "led_active_low", True),
            }
         
            conversion_warnings = get(parameters,"conversion_warnings","default")
            hexfile=get(parameters,"hexfile","")
            gen_path = os.getcwd()
            gentb=get(parameters,"gentb",False)
            print("Gentb {}".format(gentb))
            config=config.BonfireConfig()
            config.jump_bypass=get(parameters,"jump_bypass",False)
            print("jump_bypass {}".format(config.jump_bypass))

            hexfile_path = os.path.normpath(os.path.join(files_root, hexfile))
            print(f"Checking existence hex file: {hexfile_path}")
            if not os.path.isfile(hexfile_path):
                print(f"Error: Hex file '{hexfile_path}' does not exist.")
                raise FileNotFoundError(f"Hex file '{hexfile_path}' does not exist.")

            Soc = bonfire_core_soc.BonfireCoreSoC(config, hexfile=hexfile_path,soc_config=soc_config)   
            Soc.gen_soc(hdl,name,gen_path,gentb=gentb,handleWarnings=conversion_warnings)

            filelist = [ "pck_myhdl_011.vhd",name+".vhd"]
            with open(name+".core","w") as corefile:
                corefile.write(CORE_TEMPLATE.format(vlnv=vlnv,
                                                    filetype="vhdlSource-2008",
                                                    files=",".join(filelist)
                ))


        return True;
    except FileNotFoundError as err:
        return False;




def gen_test():
    from rtl import config
    import os

    try:
        opts, args = getopt.getopt(sys.argv[1:],"n" ,["hdl=","name=","gentb",
                                   "laned_memory=","path=","bram_adr_width=",
                                   "num_leds=","hexfile="])

    except getopt.GetoptError as err:
        # print help information and exit:
        print(err)  # will print something like "option -a not recognized"
        sys.exit(2)

    name_overide = ""
    hdl = "VHDL"

    laned_memory = True
    bram_adr_width = 11
    num_leds = 4
    gen_path = "vhdl_gen"
    hexfile=""
    gentb = False

    for o,a in opts:
        print(o,a)
        if o in ("-n","--name"):
            name_overide=a

        elif o == "--hdl":
            hdl=a
        elif o == "--laned_memory":
            if a in ("0","false","False"):
                laned_memory = False
            else:
                laned_memory = True
        elif o=="--bram_adr_width":
            bram_adr_width = int(a,0)
        elif o == "--num_leds":
            num_leds = int(a,0)    
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

    soc_config = {
            "bramAdrWidth": bram_adr_width,
            "LanedMemory": laned_memory,
            "numLeds": num_leds
        }

    Soc = bonfire_core_soc.BonfireCoreSoC(config,hexfile=hexfile,soc_config=soc_config)
    Soc.gen_soc(hdl,n,gen_path,gentb=gentb,handleWarnings='ignore')


# Main Entry Point

if not fusesoc_gen():
    gen_test()
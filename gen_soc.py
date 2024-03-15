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
            bram_base = get(parameters,"bram_base",0xc)
            bram_adr_width = get(parameters,"bram_adr_width",11)
            conversion_warnings = get(parameters,"conversion_warnings","default")
            hexfile=get(parameters,"hexfile","")
            gen_path = os.getcwd()
            gentb=get(parameters,"gentb",False)
            print("Gentb {}".format(gentb))
            config=config.BonfireConfig()
            
            Soc = bonfire_core_soc.BonfireCoreSoC(config,hexfile=hexfile)
            Soc.gen_soc(hdl,name,gen_path,gentb=gentb)
            
            # gen_extended_core(config,hdl,name,gen_path,
            #                   bram_adr_base=bram_base,
            #                   bramAdrWidth=bram_adr_width,
            #                   handleWarnings=conversion_warnings) 

            filelist = [ "pck_myhdl_01142.vhd",name+".vhd"]
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


# Main Entry Point

if not fusesoc_gen():
    gen_test()
from __future__ import print_function
import getopt, sys

from soc import bonfire_core_soc


def get(parameters,key,default):

    try:
        return parameters[key]
    except KeyError:
        return default


import re
import os
import datetime

def gen_extended_soc_vhdl(soc_config=None, template_path=None,gen_path=None,FileName=None):
    if soc_config is None or template_path is None:
        print("Error: soc_config and template_path must be provided.")
        return False


    entity_name=get(soc_config, "entity_name", "bonfire_core_soc_top")
    # Read template file
    try:
        with open(template_path, "r") as f:
            template = f.read()
    except FileNotFoundError:
        print(f"Error: Template file '{template_path}' not found.")
        return False

    soc_config["generated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Write output file
    if FileName is None:
        FileName=entity_name+".vhd"
    out_path = os.path.join(gen_path, FileName)
    with open(out_path, "w") as out_file:
        try:
            out_file.write(template.format(**soc_config))
        except KeyError as e:
            from string import Formatter
            missing_keys = [str(e)]
            # Try to find all missing keys by attempting to format with empty values
            formatter = Formatter()
            keys_in_template = [fname for _, fname, _, _ in formatter.parse(template) if fname]
            missing_keys = [k for k in keys_in_template if k not in soc_config]
            print(f"Error: Missing keys in soc_config: {', '.join(missing_keys)}")
            sys.exit(-1)
    print(f"Generated VHDL file: {out_path}")
    return True


def fusesoc_gen():

    import yaml
    from rtl import config

    CORE_TEMPLATE = """CAPI=2:
name: {vlnv}

filesets:
    rtl:
        file_type: {filetype}
        files: [ {files} ]

    {testbench}

targets:
    default:
        filesets: 
        - rtl
        - "simulation_target ? (tb)"


"""
    
    TEST_BENCH_TEMPLATE = """
    tb:
        file_type: {filetype}
        files: [ {files} ] 
""" 

    print(sys.argv[1])
    try:
        with open(sys.argv[1], mode='r') as f:
            p=yaml.load(f, Loader=yaml.Loader)
            print(yaml.dump(p))
            files_root=p["files_root"] # Diretory from which fusesoc is invoked (usually the bonfire-core root directory)
            parameters=p["parameters"]
            print("Generating into: {}".format(os.getcwd()))


            hdl = get(parameters,"language","VHDL")
            entity_name= get(parameters,"entity_name","bonfire_core_soc_top")
            extented_soc = get(parameters,"extended_soc",False)
            # In case of the extended_soc option the VHDL wrapper will be define the top level entity name and the
            # myhdl generated entity name by the name speciify in myhdl_entity_name
            # Without extendted_soc the myhdl generated entity will implement entity_name directly and
            # myhdl_entity_name is ignored
            if extented_soc:
                myhdl_entity_name = get(parameters,"myhdl_entity_name","bonfire_core_myhdl_top")
            else:
                myhdl_entity_name = entity_name
                #Emit  warning if myhdl_entity_name is specified
                if "myhdl_entity_name" in parameters:
                    print("Warning: 'myhdl_entity_name' parameter is ignored because 'extended_soc' is False")

            vlnv = p["vlnv"]
            os.system("rm -f *.vhd *.v *.core")

            # extended = True  # TODO to be removed
            expose_wishbone_master = get(parameters, "expose_wishbone_master", False)
            if extented_soc:
                expose_wishbone_master = True

            soc_config = {
                "bramAdrWidth": get(parameters, "bram_adr_width", 11),
                "LanedMemory": get(parameters, "laned_memory", True),
                "numLeds": get(parameters, "num_leds", 4),
                "ledActiveLow": get(parameters, "led_active_low", True),
                "exposeWishboneMaster": expose_wishbone_master,
                "entity_name": entity_name, # Name of the VHDL wrapper entity (in case of extended_soc)
                # The following entries are only used with the extended soc
                "gen_core_name": myhdl_entity_name, # Name of the myhdl generated entity
                "numGpio": get(parameters, "num_gpio", 8),
                "enableUart1": get(parameters, "enable_uart1", False),
                "enableSPI": get(parameters, "enable_spi", False),
                "numSPI": get(parameters, "num_spi", 1),
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
            # In case of extented_soc the testbench is based on a VDHL template and not generated by myhdl
            Soc.gen_soc(hdl,myhdl_entity_name,gen_path,gentb=gentb and not extented_soc,handleWarnings=conversion_warnings)

            filelist = [ "pck_myhdl_011.vhd",myhdl_entity_name+".vhd"]
            if extented_soc:
                print("Generating extended soc vhdl")
                template_path = os.path.normpath(os.path.join(files_root, "soc/vhdl/soc_top.vhd"))
                if not gen_extended_soc_vhdl(soc_config=soc_config,
                                            template_path=template_path,
                                            gen_path=gen_path):
                    print("Error generating extended soc vhdl")
                    return False

                filelist.append(entity_name+".vhd") # Add wrapper file to filelist

                print("Generating extended soc vhdl testbench")
                template_path = os.path.normpath(os.path.join(files_root, "soc/vhdl/tb_soc.vhd"))
                TBFileName="tb_"+entity_name+".vhd"
                if not gen_extended_soc_vhdl(soc_config=soc_config,
                                            template_path=template_path,
                                            gen_path=gen_path,
                                            FileName=TBFileName):
                    print("Error generating extended soc vhdl")
                    return False
                # Create a fileset for the testbench
                testbench = TEST_BENCH_TEMPLATE.format(filetype="vhdlSource-2008",
                                                       files=TBFileName)
                testbench_fileset = " ,tb"
            else:
                testbench = ""
                testbench_fileset = ""

            with open(f"{entity_name}.core","w") as corefile:
                corefile.write(CORE_TEMPLATE.format(vlnv=vlnv,
                                                    filetype="vhdlSource-2008",
                                                    files=",".join(filelist),
                                                    testbench=testbench,
                                                    testbench_fileset=testbench_fileset
                ))
            print(f"Generated {entity_name}.core")


        return True;
    except FileNotFoundError as err:
        return False;




def gen_test():
    from rtl import config
    import os

    try:
        opts, args = getopt.getopt(sys.argv[1:],"n" ,["hdl=","name=","gentb",
                                   "laned_memory=","path=","bram_adr_width=",
                                   "num_leds=","hexfile=","expose_wishbone_master","extended_soc",
                                   "vhdl_template_path="])

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
    expose_wishbone_master = False
    extended_soc = False
    vhdl_template_path = "soc/vhdl/soc_top.vhd"

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
        elif o == "--expose_wishbone_master":
            expose_wishbone_master = True
        elif o == "--extended_soc":
            extended_soc = True
        elif o == "--vhdl_template_path":
            vhdl_template_path = a

    config=config.BonfireConfig()
    config.jump_bypass = False

    # Name of the myhdl generated entity
    if name_overide:
        n=name_overide
    else:
        if gentb:
            n="bonfire_core_soc_tb"
        else:
            n="bonfire_core_soc_top"
            if extended_soc:
                n="bonfire_core_myhdl_top"

    soc_config = {
            "bramAdrWidth": bram_adr_width,
            "LanedMemory": laned_memory,
            "numLeds": num_leds,
            "exposeWishboneMaster": expose_wishbone_master,
            "numGpio": 8,
            "enableUart1": True,
            "enableSPI": True,
            "entity_name": "bonfire_core_soc_top", # Name of the VHDL wrapper entity (in case of extended_soc)
            "gen_core_name": n, # Name of the myhdl generated entity
            "numSPI": 1
        }

    Soc = bonfire_core_soc.BonfireCoreSoC(config,hexfile=hexfile,soc_config=soc_config)
    Soc.gen_soc(hdl,n,gen_path,gentb=gentb,handleWarnings='ignore')
    if extended_soc:
        gen_extended_soc_vhdl(soc_config=soc_config,
                              template_path=vhdl_template_path,
                              gen_path=gen_path)


# Main Entry Point

if not fusesoc_gen():
    gen_test()
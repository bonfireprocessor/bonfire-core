from __future__ import print_function

from tb import  tb_barrel_shifter, tb_alu,tb_decode,tb_regfile,tb_simple_pipeline,tb_loadstore,tb_fetch,tb_core

from uncore import tb_soc
from soc import bonfire_core_soc

from rtl import config

import getopt, sys, traceback



def test(inst,**kwagrs):
    kwagrs["directory"]="./waveforms"
    inst.config_sim(**kwagrs)

    try: 
        if 'duration' in kwagrs:
            d=kwagrs['duration']
        else:
            d=10000
        inst.run_sim(duration=d)
    except AssertionError as a:
        print("Test failure: "," ".join(a.args))
        traceback.print_exc()
        inst.quit_sim()
        print("stopping simulation run because of test failure")
        sys.exit(0)
    # except ValueError as err:
    #     print("Exception: " + err.message)
    #     inst.quit_sim()
    #     print("stopping simulation run")
    #     exit()


    inst.quit_sim()

def convert_tb(inst,**kwargs):
    inst.convert(**kwargs)


def module_unit_tests():
    print("Testing tb_barrel_left_shift_comb")
    test(tb_barrel_shifter.tb_barrel_left_shift_comb())
    print("OK")

    print("Testing tb_barrel_left_shift_pipelined")
    test(tb_barrel_shifter.tb_barrel_left_shift_pipelined(),trace=False)
    print("OK")

    print("Testing tb_barrel_shift_pipelined")
    test(tb_barrel_shifter.tb_barrel_shift_pipelined(),trace=False)
    print("OK")

    print('Testing alu c_shifter_mode="behavioral"')
    test(tb_alu.tb(c_shifter_mode="behavioral"),trace=False)
    print("OK")

    print('Testing alu c_shifter_mode="comb"')
    test(tb_alu.tb(c_shifter_mode="comb"),trace=False)
    print("OK")

    print('Testing alu c_shifter_mode="pipelined"')
    test(tb_alu.tb(c_shifter_mode="pipelined"),trace=False)
    print("OK")

    print('Testing decoder')
    test(tb_decode.tb(),trace=False)
    print("OK")

    print('Testing Regfile')
    test(tb_regfile.tb(),trace=False)
    print("OK")

def loadstore_unit_tests():    
    print('Testing Loadstore')
    conf=config.BonfireConfig()
    # Waveform tracing test variant
    conf.loadstore_outstanding=1
    conf.registered_read_stage=False
    test(tb_loadstore.tb(config=conf,test_conversion=False),trace=False,filename="tb_loadstore")

    # Other variants
    for i in range(1,3):
        conf.loadstore_outstanding=i
        test(tb_loadstore.tb(config=conf,test_conversion=False),trace=False)

    conf.registered_read_stage=True
    for i in range(1,4):
        conf.loadstore_outstanding=i
        test(tb_loadstore.tb(config=conf,test_conversion=False),trace=False)


def pipeline_integration_tests():
    print('Testing SimplePipeline with comb shifter')
    conf=config.BonfireConfig()
    conf.shifter_mode="comb"
    test(tb_simple_pipeline.tb(config=conf),trace=False,filename="tb_simple_pipeline_comb_shift")


    print('Testing SimplePipeline with staged shifter')
    test(tb_simple_pipeline.tb(test_conversion=False),trace=False,filename="tb_simple_pipeline")

    print('Testing Fetch unit')
    test(tb_fetch.tb(test_conversion=False),trace=False,filename="tb_fetch")

def core_integration_tests(hex,elf,sig,vcd,verbose):   
    tb=tb_core.tb(hexFile=hex,elfFile=elf,sigFile=sig,ramsize=16384,verbose=verbose)
    test(tb,trace=bool(vcd),filename=vcd,duration=20000)
    

def soc_test(hex,vcd,elf,sig):
    tb=tb_soc.tb(hexFile=hex,elfFile=elf,sigFile=sig)
    test(tb,trace=bool(vcd),filename=vcd,duration=20000)
    
    
def new_soc_test(hex,vcd):
    conf = config.BonfireConfig()
    conf.jump_bypass = False
    Soc = bonfire_core_soc.BonfireCoreSoC(conf,hexfile=hex)
    tb=Soc.soc_testbench()
    test(tb,trace=bool(vcd),filename=vcd,duration=20000)
    

try:
    opts, args = getopt.getopt(sys.argv[1:],"e:,x:v" ,
    ["elf=","hex=","ut_modules","ut_loadstore", "pipeline","all","soc","ut_cache","new_soc","vcd=","sig="])
except getopt.GetoptError as err:
    # print help information and exit:
    print(err)  # will print something like "option -a not recognized"
    sys.exit(2)


def cache_unit_tests():
    from tb import tb_cache

    #test(tb_cache.tb_tagram(),trace=False)
    #test(tb_cache.tb_cache_way(test_conversion=True),trace=False)
    test(tb_cache.tb_cache(test_conversion=False ,cache_size_m_words=128, master_data_width=128, verbose=False ,pipelined=True),trace=True)


### Main....    

elfname=""
hexname=""
vcdname=""
signame=""

options=[]

for o,a in opts:
    print(o,a)
    if o in ("-e","--elf"):
        elfname=a
    elif o in ("-x","--hex"):
        hexname=a
    elif o == "--vcd":
        vcdname=a
    elif o == "--sig":
        signame=a    
    else:
        options.append(o)
   


if "--all" in options or "--ut_modules" in options:
    module_unit_tests()

if "--all" in options or "--ut_loadstore" in options:
    loadstore_unit_tests()    

if "--all" in options or "--pipeline" in options:
    pipeline_integration_tests()

if "--ut_cache" in options:
    cache_unit_tests()

if hexname:
    if "--soc" in options:
        soc_test(hexname,vcdname,elfname,signame)
    elif "--new_soc" in options:
        new_soc_test(hexname,vcdname)
    else:     
        core_integration_tests(hexname,elfname,signame,vcdname,"-v" in options)



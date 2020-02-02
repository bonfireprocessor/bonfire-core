from tb import  tb_barrel_shifter, tb_alu,tb_decode,tb_regfile,tb_simple_pipeline,tb_loadstore,tb_fetch,tb_core

from rtl import config


def test(inst,**kwagrs):
    kwagrs["directory"]="./waveforms"
    inst.config_sim(**kwagrs)

    try: 
        inst.run_sim(duration=10000)
    except AssertionError as a:
        print("Test failure: " + a.message)
        inst.quit_sim()
        print("stopping simulation run because of test failure")
        exit()
    # except ValueError as err:
    #     print("Exception: " + err.message)
    #     inst.quit_sim()
    #     print("stopping simulation run")
    #     exit()


    inst.quit_sim()

def convert_tb(inst,**kwargs):
    inst.convert(**kwargs)


def module_unit_tests():
    print "Testing tb_barrel_left_shift_comb"
    test(tb_barrel_shifter.tb_barrel_left_shift_comb())

    print "Testing tb_barrel_left_shift_pipelined"
    test(tb_barrel_shifter.tb_barrel_left_shift_pipelined(),trace=False)

    print "Testing tb_barrel_shift_pipelined"
    test(tb_barrel_shifter.tb_barrel_shift_pipelined(),trace=False)

    print 'Testing alu c_shifter_mode="behavioral"'
    test(tb_alu.tb(c_shifter_mode="behavioral"),trace=False)

    print 'Testing alu c_shifter_mode="comb"'
    test(tb_alu.tb(c_shifter_mode="comb"),trace=False)

    print 'Testing alu c_shifter_mode="pipelined"'
    test(tb_alu.tb(c_shifter_mode="pipelined"),trace=False)

    print 'Testing decoder'
    test(tb_decode.tb(True),trace=False)

    print 'Testing Regfile'
    test(tb_regfile.tb(),trace=False)

def loadstore_unit_tests():    
    print 'Testing Loadstore'
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
    print 'Testing SimplePipeline with comb shifter'
    conf=config.BonfireConfig()
    conf.shifter_mode="comb"
    test(tb_simple_pipeline.tb(config=conf),trace=False,filename="tb_simple_pipeline_comb_shift")


    print 'Testing SimplePipeline with staged shifter'
    test(tb_simple_pipeline.tb(test_conversion=False),trace=False,filename="tb_simple_pipeline")

    print 'Testing Fetch unit'
    test(tb_fetch.tb(test_conversion=False),trace=False,filename="tb_fetch")

def core_integration_tests():
    tb=tb_core.tb(progfile="/home/thomas/development/bonfire/bonfire-core/code/simple_loop.hex",ramsize=256)
    test(tb,trace=True,filename="tb_core")
    


#module_unit_tests()
#loadstore_unit_tests()
#pipeline_integration_tests()
core_integration_tests()




from tb import  tb_barrel_shifter, tb_alu,tb_decode,tb_regfile,tb_simple_pipeline,tb_loadstore

from rtl import config


def test(inst,**kwagrs):
    kwagrs["directory"]="./waveforms"
    inst.config_sim(**kwagrs)
    inst.run_sim(duration=1000)
    inst.quit_sim()

def convert_tb(inst,**kwargs):
    inst.convert(**kwargs)



# print "Testing tb_barrel_left_shift_comb"
# test(tb_barrel_shifter.tb_barrel_left_shift_comb())

# print "Testing tb_barrel_left_shift_pipelined"
# test(tb_barrel_shifter.tb_barrel_left_shift_pipelined(),trace=False)

# print "Testing tb_barrel_shift_pipelined"
# test(tb_barrel_shifter.tb_barrel_shift_pipelined(),trace=False)

# print 'Testing alu c_shifter_mode="behavioral"'
# test(tb_alu.tb(c_shifter_mode="behavioral"),trace=False)

# print 'Testing alu c_shifter_mode="comb"'
# test(tb_alu.tb(c_shifter_mode="comb"),trace=False)

# print 'Testing alu c_shifter_mode="pipelined"'
# test(tb_alu.tb(c_shifter_mode="pipelined"),trace=False)

# print 'Testing decoder'
# test(tb_decode.tb(True),trace=False)

# print 'Testing Regfile'
# test(tb_regfile.tb(),trace=False)



# print 'Testing SimplePipeline with comb shifter'
# conf=config.BonfireConfig()
# conf.shifter_mode="comb"
# test(tb_simple_pipeline.tb(config=conf),trace=False,filename="tb_simple_pipeline_comb_shift")

# print 'Testing SimplePipeline with staged shifter'
# test(tb_simple_pipeline.tb(test_conversion=True),trace=False,filename="tb_simple_pipeline")


print 'Testing Loadstore'
conf=config.BonfireConfig()
# Waveform tracing test variant
conf.loadstore_outstanding=2
conf.registred_read_stage=False
test(tb_loadstore.tb(config=conf,test_conversion=False),trace=True,filename="tb_loadstore")
# Other variants
for i in range(1,4):
    conf.loadstore_outstanding=i
    test(tb_loadstore.tb(config=conf,test_conversion=False),trace=False)

conf.registred_read_stage=True
for i in range(1,4):
    conf.loadstore_outstanding=i
    test(tb_loadstore.tb(config=conf,test_conversion=False),trace=False)



# conf.loadstore_outstanding=2
# test(tb_loadstore.tb(config=conf,test_conversion=False),trace=False,filename="tb_loadstore")
# conf.loadstore_outstanding=3
# test(tb_loadstore.tb(config=conf,test_conversion=False),trace=False,filename="tb_loadstore")

#convert_tb(tb_barrel_shifter.tb_barrel_left_shift_comb(),hdl='VHDL',std_logic_ports=True,path='vhdl_gen_tb')






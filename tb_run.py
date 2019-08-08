from tb import  tb_barrel_shifter, tb_alu


def test(inst,**kwagrs):
    inst.config_sim(**kwagrs)
    inst.run_sim()
    inst.quit_sim()

def convert_tb(inst,**kwargs):
    inst.convert(**kwargs)



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

convert_tb(tb_barrel_shifter.tb_barrel_left_shift_comb(),hdl='VHDL',std_logic_ports=True,path='vhdl_gen_tb')






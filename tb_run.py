from tb import  tb_barrel_shifter


def test(inst,**kwagrs):
    inst.config_sim(**kwagrs)
    inst.run_sim()
    inst.quit_sim()

def convert_tb(inst,**kwargs):
    inst.convert(**kwargs)



print "Testing tb_barrel_left_shift_comb"
test(tb_barrel_shifter.tb_barrel_left_shift_comb())

print "Testing tb_barrel_left_shift_pipelined"
test(tb_barrel_shifter.tb_barrel_left_shift_pipelined(),trace=True)

print "Testing tb_barrel_shift_pipelined"
test(tb_barrel_shifter.tb_barrel_shift_pipelined(),trace=False)

convert_tb(tb_barrel_shifter.tb_barrel_left_shift_comb(),hdl='VHDL',std_logic_ports=True,path='vhdl_gen_tb')






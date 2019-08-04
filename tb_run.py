from tb import  tb_barrel_shifter


def test(inst,**kwagrs):
    inst.config_sim(kwagrs)
    inst.run_sim()
    inst.quit_sim()



#print "Testing tb_barrel_left_shift_comb"

#test(tb_barrel_shifter.tb_barrel_left_shift_comb())

print "Testing tb_barrel_left_shift_pipelined"
test(tb_barrel_shifter.tb_barrel_left_shift_pipelined(),trace=True)


#inst.convert(hdl="VHDL",path='vhdl_gen_tb')





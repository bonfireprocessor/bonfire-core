from tb import  tb_barrel_shifter



inst=tb_barrel_shifter.tb_barrel_left_shift_comb()


inst.convert(hdl="VHDL",path='vhdl_gen_tb')

inst.config_sim(trace=False)
inst.run_sim()

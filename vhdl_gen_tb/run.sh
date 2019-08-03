python tb_run.py
ghdl -a pck_myhdl_011.vhd
ghdl -a tb_barrel_left_shift_comb.vhd
ghdl --elab-run tb_barrel_left_shift_comb --wave=xx.ghw
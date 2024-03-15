ghdl -a --std=08 pck_myhdl_01142.vhd
ghdl -a --std=08 bonfire_core_soc_tb.vhd
ghdl  --elab-run --std=08   bonfire_core_soc_tb --wave=tbsoc.ghw
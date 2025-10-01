source edalize_yosys_procs.tcl
yosys plugin -i ghdl
#yosys ghdl --std=08 -fsynopsys src/bonfire-core-soc-soc_top_0/pck_myhdl_011.vhd
yosys ghdl --std=08 -fsynopsys src/bonfire-core-soc-soc_top_0/pck_myhdl_011.vhd \
  src/bonfire-core-soc-soc_top_0/bonfire_core_soc_top.vhd \
  src/bonfire-core-soc_0/fpga/ulx3s/ulx3_top.vhdl \
   -e $top
yosys synth_ecp5 -top $top -json $name.json


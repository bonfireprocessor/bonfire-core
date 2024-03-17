
# Efinity Interface Designer SDC
# Version: 2020.1.140
# Date: 2020-07-13 21:30

# Copyright (C) 2017 - 2020 Efinix Inc. All rights reserved.

# Device: T8F81
# Project: bonfire_basic_soc
# Timing Model: C2 (final)

# PLL Constraints
#################
create_clock -period 40.00 [get_ports {sysclk}]

# GPIO Constraints
####################
# set_input_delay -clock <CLOCK> -max <MAX CALCULATION> [get_ports {resetn}]
# set_input_delay -clock <CLOCK> -min <MIN CALCULATION> [get_ports {resetn}]
# set_input_delay -clock <CLOCK> -max <MAX CALCULATION> [get_ports {uart0_rxd}]
# set_input_delay -clock <CLOCK> -min <MIN CALCULATION> [get_ports {uart0_rxd}]
# set_output_delay -clock <CLOCK> -max <MAX CALCULATION> [get_ports {LED[0]}]
# set_output_delay -clock <CLOCK> -min <MIN CALCULATION> [get_ports {LED[0]}]
# set_output_delay -clock <CLOCK> -max <MAX CALCULATION> [get_ports {LED[1]}]
# set_output_delay -clock <CLOCK> -min <MIN CALCULATION> [get_ports {LED[1]}]
# set_output_delay -clock <CLOCK> -max <MAX CALCULATION> [get_ports {LED[2]}]
# set_output_delay -clock <CLOCK> -min <MIN CALCULATION> [get_ports {LED[2]}]
# set_output_delay -clock <CLOCK> -max <MAX CALCULATION> [get_ports {LED[3]}]
# set_output_delay -clock <CLOCK> -min <MIN CALCULATION> [get_ports {LED[3]}]
# set_output_delay -clock <CLOCK> -max <MAX CALCULATION> [get_ports {uart0_txd}]
# set_output_delay -clock <CLOCK> -min <MIN CALCULATION> [get_ports {uart0_txd}]

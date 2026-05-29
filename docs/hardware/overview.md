# Hardware Overview

This section groups the hardware-oriented documentation for the Bonfire core and its SoC-level integration.

## Scope

The current repository contains documentation and source code for:

- the configurable Bonfire RISC-V core,
- internal buses and interconnect blocks,
- block RAM integration,
- a MyHDL SoC wrapper around the core,
- an Extended SoC simulation and generation flow.

## Main implementation areas

- `rtl/` — hardware-describing MyHDL code
- `rtl/uncore/` — interconnect and RAM helper blocks
- `rtl/soc/` — SoC integration code
- `tb/` — MyHDL testbench code
- `fusesoc-cores/` — FuseSoC generator and template infrastructure

## Related source files

- `README.md`
- `soc/SOC.md`
- `soc/EXTENDED_SOC.md`
- `RTL_SOC_REFACTOR_PLAN.md`

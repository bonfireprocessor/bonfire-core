# Generation and FuseSoC

The repository contains FuseSoC core descriptions, generators, and templates for Bonfire Core and the SoC flow.

## Main locations

- `fusesoc-cores/`
- `gen_core.py`
- `gen_soc.py`
- `fusesoc.conf`

## Current role in the project

The current documentation and refactor notes indicate that:

- generator infrastructure was moved under `fusesoc-cores/`,
- root-level generator scripts remain as compatibility wrappers,
- templates are kept with the FuseSoC infrastructure.

## Related source files

- `RTL_SOC_REFACTOR_PLAN.md`
- `soc/EXTENDED_SOC.md`

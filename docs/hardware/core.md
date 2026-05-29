# Core

Bonfire Core is a modular and configurable RISC-V core implemented in MyHDL.

## Current project focus

According to the project README, the early project goals include:

- an RV32I-capable core,
- simulation-based validation,
- running small software programs on FPGA targets,
- timing and implementation feasibility work.

## Main core-related code areas

- `rtl/bonfire_core_top.py`
- `rtl/simple_pipeline.py`
- `rtl/fetch.py`
- `rtl/decode.py`
- `rtl/execute.py`
- `rtl/regfile.py`

## Notes

This page is intentionally still light. In a later pass, it should grow into a proper architectural overview with:

- pipeline stages,
- frontend/backend split,
- debug-module integration,
- configuration options.

## Related source files

- `README.md`
- implementation files under `rtl/`

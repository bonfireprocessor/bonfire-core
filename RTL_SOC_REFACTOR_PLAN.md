# RTL and Extended SoC Refactor Status

This document records the agreed refactor of the Bonfire Core SoC and Extended
SoC infrastructure. The main refactor is complete; the remaining items are
follow-up cleanup tasks.

## Goals

- Keep hardware-describing MyHDL code under `rtl/`.
- Keep MyHDL testbench and BFM code under `tb/`.
- Move FuseSoC generator infrastructure into `fusesoc-cores/`.
- Keep VHDL templates with the FuseSoC core infrastructure.
- Port the Extended SoC hello firmware into the local `code/` tree.

## Completed

### Python RTL and Testbench Layout

- `soc/bonfire_core_soc.py` moved to `rtl/soc/bonfire_core_soc.py`.
- Uncore RTL helpers moved from `uncore/` to `rtl/uncore/`.
- `soc/bonfire_core_soc_tb.py` moved to `tb/soc/bonfire_core_soc_tb.py`.
- `uncore/tb_wishbone_bfm.py` moved to `tb/uncore/tb_wishbone_bfm.py`.
- Python imports now use explicit package paths such as `rtl.soc`,
  `rtl.uncore`, `tb.soc`, and `tb.uncore`.
- The MyHDL SoC pytest and integration runner use the new layout.

### FuseSoC Generator and Templates

- SoC generator implementation moved to `fusesoc-cores/generators/gen_soc.py`.
- Core generator implementation moved to `fusesoc-cores/generators/gen_core.py`.
- Root-level `gen_soc.py` and `gen_core.py` are compatibility wrappers.
- `fusesoc-cores/bonfire-core-soc.core` and `fusesoc-cores/bonfire-core.core`
  point at the moved generator scripts.
- Extended SoC VHDL templates moved to `fusesoc-cores/templates/`.
- Generator cleanup now removes known generated output files instead of using
  broad shell cleanup.

### Extended SoC Generics

- `UART_TEST` renamed to `INST_UART_ONLY`.
- `INST_UART_ONLY` is treated as a debug/synthesis isolation switch.
- `INST_UART_ONLY` defaults to `false`.
- UART0 remains always enabled.
- `io_adr_high` remains fixed in the VHDL template.
- Useful generated settings such as `ENABLE_GPIO`, `DEBUG`, and
  `UART_FIFO_DEPTH` are parameterized.
- Board top-level files were updated to use `INST_UART_ONLY` where needed.

### Local Hello Firmware

- Added `code/soc/apps/hello/main.c` for the Extended SoC hello smoke test.
- Added local minimal SoC runtime helpers for UART, GPIO, `printk`, and compact
  `snprintf`.
- Added `hello` to `SOC_APPS`, so `make all` builds it for every SoC platform.
- Extended SoC simulation uses `code/build/soc/sim/hello.hex`.
- SoC `crt0.S` now clears `.bss` before entering `main`.
- SoC listing output now uses source interleaving without file-line references.

### Test Coverage

- Added `tests/test_extended_soc_fusesoc.py`.
- The Extended SoC test supports both global `ghdl` and the local OSS CAD Suite
  environment.
- The test verifies the hello UART output, GPIO/LED activity, and UART capture
  summary while tolerating CI-specific FuseSoC output after simulation.
- `scripts/bonfire-core --integration` includes the MyHDL and Extended SoC
  regression tests.

## Remaining Follow-Up Work

- Continue refactoring `fusesoc-cores/generators/gen_soc.py`:
  - reduce debug-style `print()` output,
  - split `generate_from_fusesoc()` into smaller orchestration helpers,
  - consider replacing the legacy `getopt` CLI compatibility mode with
    `argparse` or removing it after confirming no local workflow depends on it.
- Historic misspelled FuseSoC generate names were renamed from
  `soc_extented*` to `soc_extended*`; no compatibility aliases are kept.
- Consider whether the project should eventually move from top-level `rtl` and
  `tb` packages into a dedicated Python package namespace.

## Verification

Run from the project root unless noted otherwise:

```bash
make -C code clean all TARGET_PREFIX=riscv64-unknown-elf KEEP_ELF=1
python -m pytest -s -vv tests/test_soc_myhdl.py
fusesoc list-cores
fusesoc run --target=sim_extended ::bonfire-core-soc:0
scripts/bonfire-core --integration -q
```

When local `ghdl` is not available but the OSS CAD Suite is installed:

```bash
source ~/opt/oss-cad-new/oss-cad-suite/environment
fusesoc run --target=sim_extended ::bonfire-core-soc:0
```

`fusesoc list-cores` must list `::bonfire-core-soc:0`.

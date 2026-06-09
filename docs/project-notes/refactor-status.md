# Refactor Status

This page tracks the larger repository restructuring and SoC-related refactor
work, based on `RTL_SOC_REFACTOR_PLAN.md`.

## Goals

- Keep hardware-describing MyHDL code under `rtl/`.
- Keep MyHDL testbench and BFM code under `tb/`.
- Move FuseSoC generator infrastructure into `fusesoc-cores/`.
- Keep VHDL templates with the FuseSoC core infrastructure.
- Port the Extended SoC hello firmware into the local `code/` tree.

---

## Completed items

### Python RTL and testbench layout

- `soc/bonfire_core_soc.py` → `rtl/soc/bonfire_core_soc.py`
- Uncore RTL helpers → `rtl/uncore/`
- `soc/bonfire_core_soc_tb.py` → `tb/soc/bonfire_core_soc_tb.py`
- `uncore/tb_wishbone_bfm.py` → `tb/uncore/tb_wishbone_bfm.py`
- Python imports now use explicit package paths: `rtl.soc`, `rtl.uncore`,
  `tb.soc`, `tb.uncore`.

### FuseSoC generator and templates

- SoC generator → `fusesoc-cores/generators/gen_soc.py`
- Core generator → `fusesoc-cores/generators/gen_core.py`
- Root-level `gen_soc.py` and `gen_core.py` are compatibility wrappers.
- `fusesoc-cores/bonfire-core-soc.core` and `fusesoc-cores/bonfire-core.core`
  point at the moved generator scripts.
- Extended SoC VHDL templates → `fusesoc-cores/templates/`
- Generator cleanup now removes known generated output files instead of using
  broad shell cleanup.

### Extended SoC generics

- `UART_TEST` renamed to `INST_UART_ONLY`.
- `INST_UART_ONLY` defaults to `false`.
- UART0 remains always enabled.
- `io_adr_high` remains fixed in the VHDL template.
- Useful settings such as `ENABLE_GPIO`, `DEBUG`, and `UART_FIFO_DEPTH` are
  parameterized.
- Board top-level files updated to use `INST_UART_ONLY`.

### Local hello firmware

- Added `code/soc/apps/hello/main.c` for the Extended SoC UART/GPIO smoke test.
- Added local minimal SoC runtime helpers for UART, GPIO, `printk`, and compact
  `snprintf`.
- Added `hello` to `SOC_APPS` so `make all` builds it for every SoC platform.
- Extended SoC simulation uses `code/build/soc/sim/hello.hex`.
- SoC `crt0.S` now clears `.bss` before entering `main`.
- SoC listing output uses source interleaving without file-line references.

### Test coverage

- Added `tests/test_extended_soc_fusesoc.py`.
- The test supports both global `ghdl` and the local OSS CAD Suite environment.
- The test verifies UART output, GPIO/LED activity, and UART capture summary.
- `scripts/bonfire-core --integration` includes the MyHDL and Extended SoC
  regression tests.
- Core integration now runs each discovered core-test HEX image with the debug
  module both disabled and enabled.
- Added dedicated debug-module regression coverage for DMI, JTAG, debug CSR
  access, `ebreakm`, and single-step behavior.
- Added VHDL conversion coverage for `JtagDTM` and JTAG-enabled SoC generation.

---

## Remaining follow-up work

- Continue refactoring `fusesoc-cores/generators/gen_soc.py`:
  - reduce debug-style `print()` output,
  - split `generate_from_fusesoc()` into smaller orchestration helpers,
  - consider replacing the legacy `getopt` CLI compatibility mode with
    `argparse`.
- Revisit the IcePi Zero timing path that now runs through load/store, execute,
  and debug `dpc` update logic after JTAG debug enablement.
- Consider whether the project should eventually move from top-level `rtl` and
  `tb` packages into a dedicated Python package namespace.

---

## Verification

Run from the project root:

```bash
make -C code clean all TARGET_PREFIX=riscv64-unknown-elf KEEP_ELF=1
python -m pytest -s -vv tests/test_soc_myhdl.py
fusesoc list-cores
fusesoc run --target=sim_extended ::bonfire-core-soc:0
scripts/bonfire-core --integration -q
```

With OSS CAD Suite instead of a global `ghdl`:

```bash
source ~/opt/oss-cad-new/oss-cad-suite/environment
fusesoc run --target=sim_extended ::bonfire-core-soc:0
```

`fusesoc list-cores` must list `::bonfire-core-soc:0`.

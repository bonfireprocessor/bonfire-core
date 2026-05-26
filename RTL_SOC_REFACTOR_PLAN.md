# RTL and Extended SoC Refactor Plan

This plan documents the agreed refactoring sequence for the Bonfire Core SoC
and Extended SoC infrastructure.

## Goals

- Keep hardware-describing MyHDL code under `rtl/`.
- Keep MyHDL testbench and BFM code under `tb/`.
- Move FuseSoC generator infrastructure into `fusesoc-cores/`.
- Keep VHDL templates with the FuseSoC core infrastructure.
- Port the Extended SoC hello firmware into the local `code/` tree.

## Step 1: Python RTL and Testbench Layout

- Move `soc/bonfire_core_soc.py` to `rtl/soc/bonfire_core_soc.py`.
- Move uncore RTL helpers from `uncore/` to `rtl/uncore/`.
- Move `soc/bonfire_core_soc_tb.py` to `tb/soc/bonfire_core_soc_tb.py`.
- Move `uncore/tb_wishbone_bfm.py` to `tb/uncore/tb_wishbone_bfm.py`.
- Update all Python imports to use explicit absolute package paths.
- Verify with import checks, compile checks, and the existing MyHDL SoC pytest.

## Step 2: FuseSoC Generator and Templates

- Move the generator implementation to `fusesoc-cores/generators/gen_soc.py`.
- Point `fusesoc-cores/bonfire-core-soc.core` at the new generator script.
- Move VHDL templates to `fusesoc-cores/templates/`.
- Refactor generator code into focused helpers for parameter handling, path
  resolution, template rendering, MyHDL conversion, and generated core output.
- Replace broad shell cleanup with explicit generated-file cleanup.

## Step 3: Extended SoC Generics

- Rename `UART_TEST` to `INST_UART_ONLY`.
- Use `INST_UART_ONLY` only as a debug/synthesis isolation switch.
- Default `INST_UART_ONLY` to `false`.
- Keep UART0 always enabled.
- Keep `io_adr_high` fixed in the VHDL template.
- Parameterize only the useful existing hard-coded settings such as
  `ENABLE_GPIO`, `DEBUG`, and `UART_FIFO_DEPTH`.
- Update board top-level files to use `INST_UART_ONLY` where needed.

## Step 4: Local Hello Firmware

- Add a local `code/soc/apps/hello/main.c`.
- Port behavior from the external `sim_hello.c` instead of copying the old
  runtime.
- Add only minimal UART/console helpers needed by the app.
- Add `hello` to `SOC_APPS` so `make all` builds it for all SoC platforms.
- Use `code/build/soc/sim/hello.hex` for Extended SoC simulation.

## Verification

Run from the project root unless noted otherwise:

```bash
make -C code clean all TARGET_PREFIX=riscv64-unknown-elf KEEP_ELF=1
python -m pytest -s -vv tests/test_soc_myhdl.py
fusesoc list-cores
source ~/opt/oss-cad-new/oss-cad-suite/environment && fusesoc run --target=sim_extended ::bonfire-core-soc:0
scripts/bonfire-core --integration -q
```

`fusesoc list-cores` must list `::bonfire-core-soc:0`.

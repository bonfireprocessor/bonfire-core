# Bonfire Core Documentation

Bonfire Core is a configurable RISC-V core written in MyHDL, together with SoC
wrappers, test infrastructure, and small software test programs.

## What you will find here

- **[Getting Started](getting-started/overview.md)** — set up the environment
  and run the test suite.
- **[Hardware](hardware/overview.md)** — architecture of the core, SoC, and
  extended SoC.
- **[Workflows](workflows/overview.md)** — day-to-day developer workflows.
- **[Software](software/overview.md)** — test programs, SoC firmware, and
  compliance testing.
- **[Project Notes](project-notes/refactor-status.md)** — refactor history and
  status.

## Quick orientation

### Processor core

The processor is a 3-stage in-order pipeline (Fetch → Decode → Execute)
implementing the RV32I base ISA with optional debug module support.
See [Core](hardware/core.md).

### SoC

`BonfireCoreSoC` wraps the core with block RAM, a native LED register, and a
Wishbone master bridge. `bonfireCoreExtendedInterface` is the lower-level
integration block that connects the CPU to memory and buses.
See [SoC](hardware/soc.md).

### Extended SoC

A FuseSoC generator converts the MyHDL SoC to VHDL and optionally wraps it
with a VHDL peripheral block (UART, GPIO, SPI). This path supports
simulation via GHDL and synthesis to multiple FPGA targets.
See [Extended SoC](hardware/extended-soc.md).

## Quick start

```bash
git clone https://github.com/bonfireprocessor/bonfire-core.git
cd bonfire-core
scripts/bonfire-core --install
make -C code all TARGET_PREFIX=riscv64-unknown-elf KEEP_ELF=1
scripts/bonfire-core --all
```

See [Quick Start](getting-started/quick-start.md) for the full walkthrough.

## Source documents

This documentation is derived from and supersedes the following in-tree
Markdown files:

- `README.md`
- `soc/SOC.md`
- `soc/EXTENDED_SOC.md`
- `scripts/README.md`
- `tests/README.md`
- `code/README.md`
- `COMPLIANCE.md`
- `TB_RUN.md`
- `RTL_SOC_REFACTOR_PLAN.md`

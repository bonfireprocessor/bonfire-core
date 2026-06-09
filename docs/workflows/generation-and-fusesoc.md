# Generation and FuseSoC

This page describes the FuseSoC-based generation and synthesis flow.

## Overview

The repository uses [FuseSoC](https://fusesoc.readthedocs.io/) for:

- converting MyHDL RTL to VHDL (core and SoC),
- generating VHDL wrappers and testbenches from templates,
- invoking simulation (GHDL) and synthesis (Yosys, Vivado, Efinity, Gowin) backends.

## Core descriptions

| File | Covers |
| --- | --- |
| `fusesoc-cores/bonfire-core.core` | Bonfire CPU core alone |
| `fusesoc-cores/bonfire-core-soc.core` | Bonfire Core SoC (core + RAM + peripherals) |

Root-level `gen_core.py` and `gen_soc.py` are compatibility wrappers that
forward to the real implementations in `fusesoc-cores/generators/`.

## Listing available cores

From the project root (where `fusesoc.conf` lives):

```bash
fusesoc list-cores
```

`::bonfire-core-soc:0` must appear in the output.

## Generator flow

FuseSoC calls a Python generator for each `generate:` block defined in the
`.core` file:

```yaml
generators:
  gen_bonfire_core_soc:
    interpreter: python3
    command: generators/gen_soc.py
```

The generator:

1. Converts `rtl/soc/bonfire_core_soc.py` from MyHDL to VHDL.
2. Optionally generates a VHDL wrapper from
   `fusesoc-cores/templates/soc_top.vhd` (Extended SoC path).
3. Optionally generates a VHDL testbench from
   `fusesoc-cores/templates/tb_soc.vhd`.
4. Writes a generated `.core` file listing the generated VHDL files.

The generator configuration now also accepts `enable_jtag_debug`, which maps to
`enableJtagDebug` inside the MyHDL SoC and exposes a `JtagDTM` transport plus
the corresponding JTAG pins on the generated entity.

Generated files end up under `build/bonfire-core-soc_0/<target>/generator_cache/`.

## Simulation targets

### MyHDL SoC simulation (pytest-based)

```bash
pytest -vv tests/test_soc_myhdl.py
```

### Basic VHDL SoC simulation (GHDL via FuseSoC)

```bash
fusesoc run --target=sim ::bonfire-core-soc:0
```

The `sim` target enables JTAG debug so the generated MyHDL SoC testbench can
exercise the debug path during conversion and GHDL smoke tests.

### Extended SoC VHDL simulation (GHDL via FuseSoC)

```bash
fusesoc run --target=sim_extended ::bonfire-core-soc:0
```

Or via pytest:

```bash
pytest -vv tests/test_extended_soc_fusesoc.py
```

With the OSS CAD Suite:

```bash
source ~/opt/oss-cad-suite/environment
fusesoc run --target=sim_extended ::bonfire-core-soc:0
```

## FPGA synthesis targets

| Target | Board | Toolchain |
| --- | --- | --- |
| `FireAnt` | Efinix Trion T8 (FireAnt) | Efinity |
| `ulx3s` | Radioana ULX3S (Lattice ECP5-85) | Yosys/nextpnr/trellis |
| `ulx3s_extended` | ULX3S with Extended SoC | Yosys/nextpnr/trellis |
| `icepizero` | iCE40 IcePi Zero | Yosys/nextpnr/ice40 |
| `icepizero_extended` | IcePi Zero with Extended SoC | Yosys/nextpnr/ice40 |
| `cmods7` | Digilent Cmod S7 | Vivado |
| `cmods7_extended` | Cmod S7 with Extended SoC | Vivado |
| `synth-gowin` | Gowin-based boards | Gowin tools |

### Example: FireAnt

```bash
export EFINITY_HOME=<Your Efinity Software install dir>
fusesoc --cores-root . run --target=FireAnt bonfire-core-soc
```

### Example: ULX3S

```bash
# Activate OSS-CAD environment (adjust path)
source ~/opt/oss-cad-suite/environment
fusesoc --cores-root . run --target=ulx3s bonfire-core-soc
```

### Example: Cmod S7 (Vivado)

```bash
fusesoc run --target=cmods7_extended ::bonfire-core-soc:0
```

### IcePi Zero debug pins

The non-extended `icepizero` target now forwards the JTAG debug interface from
the generated SoC top-level to fixed Raspberry Pi GPIO header pins in
`fusesoc-cores/fpga/icepizero/board.lpf`.

## Bonfire extended core (bonfire-library dependency)

The extended SoC targets depend on the `bonfire-library` FuseSoC library.
By default `fusesoc.conf` fetches it from GitHub automatically. For local
development you can pin it to a local checkout:

```bash
fusesoc library add --sync-type=local bonfire-library ../bonfire-library
```

## File structure

| Path | Description |
| --- | --- |
| `fusesoc-cores/` | FuseSoC core descriptions, generators, and templates |
| `fusesoc-cores/generators/gen_soc.py` | SoC generator implementation |
| `fusesoc-cores/generators/gen_core.py` | Core generator implementation |
| `fusesoc-cores/templates/soc_top.vhd` | Extended SoC VHDL wrapper template |
| `fusesoc-cores/templates/tb_soc.vhd` | Extended SoC testbench template |
| `gen_soc.py` | Root-level compatibility wrapper |
| `gen_core.py` | Root-level compatibility wrapper |
| `fusesoc.conf` | FuseSoC configuration (library paths) |

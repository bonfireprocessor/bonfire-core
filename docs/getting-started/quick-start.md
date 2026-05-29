# Quick Start

This page is meant as a practical end-to-end starting point:

1. clone the repository,
2. install the required dependencies,
3. run the main tests,
4. run the SoC in the pure MyHDL testbench,
5. run the Extended SoC through FuseSoC/GHDL,
6. build an FPGA target.

## 1. Clone the repository

```bash
git clone https://github.com/bonfireprocessor/bonfire-core.git
cd bonfire-core
```

## 2. Install dependencies

### Python environment

The recommended setup uses the repo-local virtual environment:

```bash
scripts/bonfire-core --install
```

That creates or refreshes `./.venv` and installs the Python dependencies used by the test and generator flow.

If you prefer to do it manually:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install myhdl==0.11.51 pyelftools pytest
```

### RISC-V toolchain

You need a non-Linux RISC-V ELF toolchain, typically `riscv64-unknown-elf-*`.

Example for Debian/Trixie:

```bash
sudo apt install \
  binutils-riscv64-unknown-elf \
  gcc-riscv64-unknown-elf \
  picolibc-riscv64-unknown-elf \
  libstdc++-riscv64-unknown-elf-picolibc
```

### FuseSoC / simulator tools

For the VHDL-based SoC flow you also need:

- `fusesoc`
- `ghdl`

If you want to build FPGA targets, you also need the matching backend tools for the selected target, for example:

- **Vivado** for `cmods7` targets
- **Yosys/nextpnr/trellis** for `ulx3s` and `icepizero`
- **Efinity** for `FireAnt`
- **Gowin** tools for `synth-gowin`

## 3. Run the standard test suite

The recommended entry point is the universal runner:

```bash
scripts/bonfire-core --all -v
```

That covers the normal pytest-based regression flow.

Example output (shortened to the beginning and end of the run):

```text
$ scripts/bonfire-core --all -v
riscv64-unknown-elf-size build/basic_alu.elf
   text    data     bss     dec     hex filename
    260       0       0     260     104 build/basic_alu.elf
riscv64-unknown-elf-size build/simple_loop.elf
   text    data     bss     dec     hex filename
     56       0       0      56      38 build/simple_loop.elf
...
============================= test session starts ==============================
...
============================== 35 passed in 81s ===============================
```

Useful narrower variants:

```bash
scripts/bonfire-core --ut
scripts/bonfire-core --integration
```

If you prefer direct pytest:

```bash
. .venv/bin/activate
pytest
```

## 4. Build the software test images

Many tests and SoC runs expect generated firmware or test HEX files.

Build everything:

```bash
make -C code clean
make -C code all TARGET_PREFIX=riscv64-unknown-elf KEEP_ELF=1
```

This generates:

- core test programs under `code/build/core-tests/`
- SoC firmware under `code/build/soc/<platform>/`

## 5. Run the SoC in the MyHDL testbench

The modern pytest-based entry point is:

```bash
pytest -vv tests/test_soc_myhdl.py
```

This runs the pure MyHDL SoC testbench and covers:

- the LED smoke test firmware,
- the Wishbone smoke test firmware.

The historical equivalent was `tb_run.py --new_soc`.

If you want the old direct flow for quick experiments, the legacy command is still:

```bash
python tb_run.py --new_soc --hex=code/build/soc/sim/led.hex
```

## 6. Run the Extended SoC with FuseSoC

First build the simulation firmware image used by the Extended SoC flow:

```bash
make -C code soc SOC_APP=hello SOC_PLATFORM=sim TARGET_PREFIX=riscv64-unknown-elf
```

Then run the Extended SoC VHDL simulation:

```bash
fusesoc run --target=sim_extended ::bonfire-core-soc:0
```

This uses the FuseSoC generator flow plus GHDL and exercises the generated Extended SoC wrapper around the MyHDL SoC.

There is also a pytest wrapper for this regression:

```bash
pytest -vv tests/test_extended_soc_fusesoc.py
```

## 7. Build an FPGA target

The repository already contains several FuseSoC targets for FPGA builds in `fusesoc-cores/bonfire-core-soc.core`.

Examples include:

- `cmods7`
- `cmods7_extended`
- `ulx3s`
- `ulx3s_extended`
- `icepizero`
- `icepizero_extended`
- `FireAnt`
- `synth-gowin`

### Build the matching firmware first

For FPGA builds, generate a firmware image for the target platform first.

Examples:

```bash
make -C code soc SOC_APP=led SOC_PLATFORM=icepizero TARGET_PREFIX=riscv64-unknown-elf
make -C code soc SOC_APP=hello SOC_PLATFORM=ulx3s TARGET_PREFIX=riscv64-unknown-elf
make -C code soc SOC_APP=hello SOC_PLATFORM=cmods7 TARGET_PREFIX=riscv64-unknown-elf
```

### Run a build target

Example non-extended build:

```bash
fusesoc run --target=icepizero ::bonfire-core-soc:0
```

Example extended build:

```bash
fusesoc run --target=ulx3s_extended ::bonfire-core-soc:0
```

Vivado example:

```bash
fusesoc run --target=cmods7_extended ::bonfire-core-soc:0
```

The exact output bitstream/artifact location depends on the backend flow and target.

## Suggested first path

If you only want to confirm that the repository works on your machine, this is the shortest useful sequence:

```bash
git clone https://github.com/bonfireprocessor/bonfire-core.git
cd bonfire-core
scripts/bonfire-core --install
make -C code all TARGET_PREFIX=riscv64-unknown-elf KEEP_ELF=1
scripts/bonfire-core --all -v
pytest -vv tests/test_soc_myhdl.py
make -C code soc SOC_APP=hello SOC_PLATFORM=sim TARGET_PREFIX=riscv64-unknown-elf
fusesoc run --target=sim_extended ::bonfire-core-soc:0
```

## Related source files

- `README.md`
- `scripts/README.md`
- `tests/README.md`
- `code/README.md`
- `TB_RUN.md`
- `soc/SOC.md`
- `soc/EXTENDED_SOC.md`
- `fusesoc-cores/bonfire-core-soc.core`

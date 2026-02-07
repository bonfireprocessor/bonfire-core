# A RISC-V Core in MyHDL

Bonfire Core is an modular, configurable RISC-V core written in MyHDL. 

## First milestone
The first design milestone is reached and passes the following goals:

* Implement rv32i subset without any privilege mode features (no CSRs, no interrupts, no traps). 
* Pass riscv-compliance suite in MyHDL based simulation except the tests which require on traps/ CSRs to work (I-EBREAK-01, I-ECALL-01, I-MISALIGN_JMP-01,I-MISALIGN_LDST-01  )
* Be able to run a simple test pogram written in C on a real FPGA
* Reach clock frequencies comparable to bonfire-cpu


This is of course not enough to have a fully usable CPU, but allows to check the feasbilty of the design. 

The FPGA implementation is not part of this project, it is part of the bonfire-basic-soc project, contained in an experimental "bonfire_core" branch. The implementation cuts a few corners, because the single purpose of it is to have a PoC running on an FPGA. The implementation was tested on a Digilent Arty A7 board and the Trion T8 based FireAnt board. 

## Prerequisites

### Python + venv
- **Python** (tested with **Python 3.8 .. 3.13.5**) + `pip`
- Recommended: use a **virtual environment** in the repo (`.venv/`)

Quick setup (recommended): use the universal runner to create/update the venv and install deps:

```bash
cd bonfire-core
scripts/bonfire-core --install
```

Manual setup (if you prefer):

```bash
cd bonfire-core
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install myhdl==0.11.51 pyelftools pytest
```

### Python packages
- **MyHDL 0.11** (for the FuseSoC generators use **0.11.51**)
- **pytest** (test runner / framework)
- **pyelftools** (required for extracting signature symbols when running the riscv-compliance suite)

### RISC-V toolchain
- RISC-V non-Linux toolchain (`riscv64-unknown-elf-*`) with support for `rv32i` (multilib)

In the past I recommended building the latest RISC-V toolchain from source. Linux distributions are better now.
Example for Debian Trixie (incl. picolibc):

```bash
sudo apt install \
  binutils-riscv64-unknown-elf \
  gcc-riscv64-unknown-elf \
  picolibc-riscv64-unknown-elf \
  libstdc++-riscv64-unknown-elf-picolibc
```

See also hint below to compile with picolibc.

## Running tests

For day-to-day development, the recommended entry point is the universal runner:

- [`scripts/bonfire-core`](scripts/bonfire-core)

Quick test run (unit + integration):

```bash
cd bonfire-core
scripts/bonfire-core --install
scripts/bonfire-core --all
```

To run specific test groups, see the runner documentation:

- [`scripts/README.md`](scripts/README.md)

### Experts: run pytest directly

The test suite is implemented with **pytest** and can also be run directly.
Test-suite overview (groups, mapping, environment variables) is documented here:

- [`tests/README.md`](tests/README.md)

### Legacy tb_run.py / Compliance

The legacy runner **`tb_run.py`** is still available for debugging/compatibility:
- [`TB_RUN.md`](TB_RUN.md)

RISC-V compliance testing (riscv-compliance harness + signature dumping):
- [`COMPLIANCE.md`](COMPLIANCE.md)

(see above)

# New Bonfire Core SOC

Bonfire Core SoC is a SoC written in MyHDL. 
It uses FuseSoC and the Generator feature of FuseSoC to generate VHDL files and run simulators and FPGA Build Toolchains.

There is a Generator for generating a Test Bench and for generating a Toplevel Module for FPGAs

### Creating Test Code ledslow and ledsim
Clone the repo https://github.com/bonfireprocessor/bonfire-software.git
Switch to branch lfs_migrate (the master branch is not updated yet...)
execute these commands:

    cd test
    make ARCH=rv32i_zicsr_zifencei PLATFORM=BONFIRE_CORE ledsim.hex ledslow.hex

Hint: When using the latest Toolchain in Debian Trixie (which uses picolibc instead of newlib) the make command should look like this:

    make ARCH=rv32i_zicsr_zifencei PLATFORM=BONFIRE_CORE LINKSPECS=picolibc.specs ledsim.hex ledslow.hex



### Running the MyHDL Testbench



    python tb_run.py  --new_soc --hex=../bonfire-software/test/ledsim.hex  [ -vcd=<vcdfile> ]

The Output should look like this:
````
eof at adr:0x54
Created  laned ram with size 2048 words
5 3
Shifter implemented with one pipeline stage: 3:0 || 5:3 
Shifter instance with config 3 0
Shifter instance with config 5 3
Shifter instance with config 5 3
LED status @1185 ns: 1
LED status @1985 ns: 2
LED status @2785 ns: 3
LED status @3585 ns: 4
LED status @4385 ns: 5
LED status @5185 ns: 6
LED status @5985 ns: 7
LED status @6785 ns: 8
LED status @7585 ns: 9
LED status @8385 ns: a
LED status @9185 ns: b
LED status @9985 ns: c
LED status @10785 ns: d
LED status @11585 ns: e
LED status @12385 ns: f
````


### Running the VHDL Testbench
The Testbench and the Core can be converted to VHDL and run in GHDL with the following command:

    fusesoc --cores-root . run --target=sim  bonfire-core-soc

Output should look like this:
```
NFO: Preparing ::bonfire-core-soc:0
INFO: Generating ::bonfire-core-soc-soc_tb:0
...
...
Creating libraries directories
ghdl -i --std=08 --ieee=synopsys  src/bonfire-core-soc-soc_tb_0/pck_myhdl_01142.vhd src/bonfire-core-soc-soc_tb_0/tb_bonfire_core_soc.vhd
ghdl -m --std=08 --ieee=synopsys  tb_bonfire_core_soc
analyze src/bonfire-core-soc-soc_tb_0/pck_myhdl_01142.vhd
analyze src/bonfire-core-soc-soc_tb_0/tb_bonfire_core_soc.vhd
elaborate tb_bonfire_core_soc
ghdl -r --std=08 --ieee=synopsys  tb_bonfire_core_soc --ieee-asserts=disable --stop-time=20000ns --wave=cpu.ghw 
LED status @1185 ns: 1
LED status @1985 ns: 2
LED status @2785 ns: 3
LED status @3585 ns: 4
LED status @4385 ns: 5
LED status @5185 ns: 6
LED status @5985 ns: 7
LED status @6785 ns: 8
LED status @7585 ns: 9
LED status @8385 ns: A
LED status @9185 ns: B
LED status @9985 ns: C
LED status @10785 ns: D
LED status @11585 ns: E
LED status @12385 ns: F
src/bonfire-core-soc-soc_tb_0/tb_bonfire_core_soc.vhd:10178:17:@12385ns:(assertion failure): End of Simulation
./tb_bonfire_core_soc:error: assertion failed
in process .tb_bonfire_core_soc(myhdl).tb_bonfire_core_soc_observer
./tb_bonfire_core_soc:error: simulation failed
```
The "simulation failed" assertion can be ignored. There is no "info" asseration in VHDL...

### Build for FireAnt Board (Efinix Trion T8)

    export EFINITY_HOME=<Your Efinity Softtware install dir>
    fusesoc  --cores-root . run  --target FireAnt bonfire-core-soc

### Build for Radioana ULX3S (Lattice ECP5-85)

Prerequiste: Install yosys/nextpnr/trellis for example from here:
https://github.com/YosysHQ/oss-cad-suite-build


````
# Activate the oss-cad enviornment - replace ~/opt/oss-cad-suite with your installation path
source ~/opt/oss-cad-suite/environment
fusesoc --cores-root . run --target ulx3s bonfire-core-soc

````
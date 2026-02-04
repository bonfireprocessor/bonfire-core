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

Quick setup:

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

bonfire-core uses **pytest** for the test suite (unit + integration).

For an overview of the different test groups (unit tests, pipeline tests, core integration tests, etc.) see:
- [`tests/README.md`](tests/README.md)

The legacy runner **`tb_run.py`** is still available for compatibility and for some workflows (see also [`TB_RUN.md`](TB_RUN.md)).

RISC-V compliance testing (riscv-compliance harness + signature dumping) is documented here:
- [`COMPLIANCE.md`](COMPLIANCE.md)

### Run the full pytest suite
```bash
cd bonfire-core
source .venv/bin/activate
pytest
```
Expected output (example):
```text
s.......................                                                 [100%]
23 passed, 1 skipped in 4.2s
```

Show every test name + status:
```bash
pytest -vv
```
Expected output (example, shortened):
```text
============================= test session starts ==============================
platform linux -- Python 3.13.x, pytest-x.y.z
rootdir: .../bonfire-core
collected 24 items

tests/test_ut_alu.py::test_alu_comb PASSED                                [  4%]
tests/test_ut_loadstore.py::test_loadstore PASSED                          [  8%]
...
tests/test_core.py::test_core[code/trap.hex] PASSED                        [100%]

======================== 23 passed, 1 skipped in 4.2s =========================
```

Run a single file / single test:
```bash
pytest tests/test_ut_alu.py
pytest tests/test_ut_alu.py::test_alu_comb
```
Expected output (example):
```text
============================= test session starts ==============================
collected 1 item

tests/test_ut_alu.py .                                                   [100%]

============================== 1 passed in 0.2s ===============================
```

Filter by keyword:
```bash
pytest -k loadsave -vv
```
Expected output (example, shortened):
```text
collected 24 items / 23 deselected / 1 selected

tests/test_core.py::test_core[code/loadsave.hex] PASSED                   [100%]

====================== 1 passed, 23 deselected in 0.8s =======================
```

### HEX integration tests (tb_run-style monitor output)
The HEX integration tests run `tb_core` on the `code/build/*.hex` programs and check the monitor "PASS" convention.

If you want the **same console output** you used to get with `tb_run.py` (Monitor writes, etc.), run pytest with `-s`:

```bash
pytest -s -vv tests/test_core.py
```
Expected output (example, shortened):
```text
============================= test session starts ==============================
collecting ... collected 7 items

tests/test_core.py::test_core[code/build/basic_alu.hex] PASSED             [ 14%]
tests/test_core.py::test_core[code/build/branch.hex] PASSED                [ 28%]
...
tests/test_core.py::test_core[code/build/trap.hex] PASSED                  [100%]

============================== 7 passed in 3.4s ===============================
```

Filter to a single program (example `loadsave`):

```bash
pytest -s -vv tests/test_core.py -k loadsave
```
Expected output (example, incl. MyHDL monitor output):
```text
collected 7 items / 6 deselected / 1 selected

tests/test_core.py::test_core[code/build/loadsave.hex]
eof at adr:0x118
Created ram with size 16384 words
5 3
Shifter implemented with one pipeline stage: 3:0 || 5:3
Shifter instance with config 3 0
Shifter instance with config 5 3
Shifter instance with config 5 3
Monitor write: @275 10000200: fa55aa55 (-95049131)
Monitor write: @595 10000204: 00005555 (21845)
Monitor write: @805 10000208: 000000aa (170)
Monitor write: @1015 1000020c: ffffffaa (-86)
Monitor write: @1225 10000210: 00000055 (85)
Monitor write: @1435 10000214: 00000055 (85)
Monitor write: @1775 10000218: fa55aa55 (-95049131)
Monitor write: @1995 1000021c: 0000fa55 (64085)
Monitor write: @2205 10000220: fffffa55 (-1451)
Monitor write: @2425 10000224: 0000aa55 (43605)
Monitor write: @2645 10000228: ffffaa55 (-21931)
Monitor write: @2925 1000022c: fa55aa55 (-95049131)
Monitor write: @3055 10000000: 00000001 (1)
PASSED

====================== 1 passed, 6 deselected in 0.7s ========================
```

Convenience wrapper (builds the `.hex` programs into `code/build/` and then runs only the core integration tests):

```bash
scripts/run_core_integration_pytest.sh -vv
scripts/run_core_integration_pytest.sh -vv -s -k loadsave
```
Expected output (example, shortened):
```text
riscv64-unknown-elf-gcc ... -o build/basic_alu.elf basic_alu.S
...
============================= test session starts ==============================
collecting ... collected 7 items

tests/test_core.py::test_core[code/build/basic_alu.hex] PASSED             [ 14%]
...
tests/test_core.py::test_core[code/build/trap.hex] PASSED                  [100%]

============================== 7 passed in 3.5s ===============================
```

### Legacy tb_run.py (still supported)
The legacy runner `tb_run.py` is still supported for debugging and some workflows, but it has been moved into a separate document:

- [`TB_RUN.md`](TB_RUN.md) (legacy runner)
- [`COMPLIANCE.md`](COMPLIANCE.md) (riscv-compliance harness + signature dumping)

Test-suite overview (pytest + mapping) is in:
- [`tests/README.md`](tests/README.md)

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
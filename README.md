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
* Python - Currently the code is tested with Python 3.8 - Python 3.13.5

* MyHDL 0.11 - for the FuseSoC Generators use 0.11.51 (as of Sep 2025 the latest version)

* pyelftools - required for extracting the test signatures when running riscv-compliance suite

* RISC-V non-Linux (riscv64-unknown-elf) toolchain with support for rv32i (the default multilib setup contains it)
  In the past I recommended building the latest RISC-V toolchain from Source. No maturity in Linux distributions is better. 
  For example Debian Trixie  contains the riscv64-unknown-elf together with picolibc:

   ```
    sudo apt install binutils-riscv64-unknown-elf \
                     gcc-riscv64-unknown-elf \
                     picolibc-riscv64-unknown-elf \
                     libstdc++-riscv64-unknown-elf-picolibc
    
   ```
   See also hint below to compile with picolibc

I think there are enough tutorials how to install all these tools (including the RISC-V toolchain) so I will not repeat it here. 

## Running tests

Currently bonfire-core does not use any test framework, like pyunit. There is a test runner tb_run.py which allows to run various tests. It has a very basic command line interface, which not really robust error handling. There are several classes of tests:

### Module unit tests
They test a singe module. Most of the tests benches are self-checking and raise an assertion on error. A few (like the barrel shifter) just output the results, so they need visual inspection of correctness. Some tests (like tb_decoder) are very rudimentary at the moment and should be improved.
The module unit tests can be invoked with 

````
python tb_run.py --ut_modules
````

### Load store unit tests
The load store unit tests can be invoked separatly and indpendant of the other unit tests. Reason is, that the loadstore module is quite complex, because it is already prepared to support a pipelined LSU, allowing back-to-back load/stores. It tests the LSU with different configurations and pipeline depths. 

The Load/Store unit tests can be invoked with 

````
python tb_run.py --ut_loadstore
````

### Pipeline integration tests
Currently bonfire-core has only three stage pipeline implemented. It is separated into a backend and the fetch unit. The pipeline integration tests test the backend alone and together with the fetch unit. 

The Pipeline integration tests can be invoked with
````
python tb_run.py --pipeline
````

### Core integration test
This test runs the complete bonfire-core in a test bench environment with 16KB of memory at address 0 and a monitor port at address range 0x10000000 - 0x1fffffff.

Writes to the monitor range will be reported to the console. In addition a write to monitor base address will stop the test bench.
Convention is that the test write an success (0x1) or error code (either 0 or -1 (0xffffffff) ) to the monitor base address.

Optionally the monitor can dump part of the memory as a signature to a file, this is used to support the riscv-compliance test suite.

The core integration test is run when the --hex option appears in the command line. It must point to file with the code to run in hex notation (just a sequence of hexadecimal coded 32 Bit words, one word by line):

```
00a00513
10000417
ffc40413
000055b7
58858593
fff50513
00a42223
...
```

There are a few test programs in the code subdirectory. With a RISC-V toolchain installed the test code can be compiled with `make all`.

One of these files can than be run with e.g:
```
python tb_run.py --hex=code/loadsave.hex
```
The tests will end with writing a result to the monitor port base address. As outlined above, writing 1 means success:
```
python tb_run.py --hex=code/loadsave.hex
--hex code/loadsave.hex
eof at adr:0x118
Created ram with size 16384 words
5 3
Shifter implemented with one pipeline stage: 3:0 || 5:3 
Shifter instance with config 3 0
Shifter instance with config 5 3
Shifter instance with config 5 3
Monitor write: @570 10000200: fa55aa55 (-95049131)
Monitor write: @1270 10000204: 00005555 (21845)
Monitor write: @1750 10000208: 000000aa (170)
Monitor write: @2230 1000020c: ffffffaa (-86)
Monitor write: @2710 10000210: 00000055 (85)
Monitor write: @3190 10000214: 00000055 (85)
Monitor write: @3930 10000218: fa55aa55 (-95049131)
Monitor write: @4430 1000021c: 0000fa55 (64085)
Monitor write: @4910 10000220: fffffa55 (-1451)
Monitor write: @5410 10000224: 0000aa55 (43605)
Monitor write: @5910 10000228: ffffaa55 (-21931)
Monitor write: @6530 1000022c: fa55aa55 (-95049131)
Monitor write: @6830 10000000: 00000001 (1)

```
The -v option will also write the executed instructions to the console:

```
python tb_run.py -v --hex=code/loadsave.hex
-v 
--hex code/loadsave.hex
eof at adr:0x118
Created ram with size 16384 words
5 3
Shifter implemented with one pipeline stage: 3:0 || 5:3 
Shifter instance with config 3 0
Shifter instance with config 5 3
Shifter instance with config 5 3
@90ns exc: 00000000 : 10000417 
@110ns exc: 00000004 : 00040413 
@130ns exc: 00000008 : 20040193 
@150ns exc: 0000000c : 00000597 
@170ns exc: 00000010 : 10458593 
@190ns exc: 00000014 : fa55b637 
.....
```

These files are mainly for intended for debugging the core. For a more complete test the riscv-compliance suite is used.

### Writing a vcd file
The parameter `--vcd=<filename>` will enable writing a vcd file (only supported for the core integration test)



## RISC-V Compliance testing

### Writing a test signature file
The RISC-V compliance  suite works in a way that every test will create a signature dump which is compared against a golden reference. The test code will write the signature into its memory, between the symbols `begin_signature` and `end_signature`

The test bench uses pyelftools to extract both symbols from the elf file of the test and then write a memory dump. The code for this is implemented in function `dump_signature` in `tb/sim_monitor.py`

The following command is used for running the compliance tests:

```
python tb_run.py  --elf=<test program elf file> --sign=<signature file name> --hex=<test program hex file>
``` 

Note: A future version may extract the code also from the elf file and make the hex file superflous. Currently it is only used for symbol extraction.


### Running riscv-compliance

The following fork of riscv-compliance has a target for bonfire-core:

https://github.com/bonfireprocessor/riscv-compliance

More information can be found in the readme file:

https://github.com/bonfireprocessor/riscv-compliance/blob/master/riscv-target/bonfire-core/README.md

The compliance test can be run with the command:
```
make PARALELL=1 JOBS="-j" RISCV_TARGET=bonfire-core BONFIRE_CORE_ROOT=<your bonfire-core root directory>
```

It will run the following test suites:

    rv32i rv32Zicsr

The result should look like this:

For rv32Zicsr

```
Check               I-CSRRC-01 ... OK
Check              I-CSRRCI-01 ... OK
Check               I-CSRRS-01 ... OK
Check              I-CSRRSI-01 ... OK
Check               I-CSRRW-01 ... OK
Check              I-CSRRWI-01 ... OK
--------------------------------
OK: 6/6 RISCV_TARGET=bonfire-core RISCV_DEVICE=rv32Zicsr RISCV_ISA=rv32Zicsr
```
For rv32i:


```
Compare to reference files ... 

Check         I-ADD-01 ... OK
Check        I-ADDI-01 ... OK
Check         I-AND-01 ... OK
Check        I-ANDI-01 ... OK
Check       I-AUIPC-01 ... OK
Check         I-BEQ-01 ... OK
Check         I-BGE-01 ... OK
Check        I-BGEU-01 ... OK
Check         I-BLT-01 ... OK
Check        I-BLTU-01 ... OK
Check         I-BNE-01 ... OK
Check I-DELAY_SLOTS-01 ... OK
Check      I-EBREAK-01 ... IGNORE
Check       I-ECALL-01 ... IGNORE
Check   I-ENDIANESS-01 ... OK
Check             I-IO ... OK
Check         I-JAL-01 ... OK
Check        I-JALR-01 ... OK
Check          I-LB-01 ... OK
Check         I-LBU-01 ... OK
Check          I-LH-01 ... OK
Check         I-LHU-01 ... OK
Check         I-LUI-01 ... OK
Check          I-LW-01 ... OK
Check I-MISALIGN_JMP-01 ... IGNORE
Check I-MISALIGN_LDST-01 ... IGNORE
Check         I-NOP-01 ... OK
Check          I-OR-01 ... OK
Check         I-ORI-01 ... OK
Check     I-RF_size-01 ... OK
Check    I-RF_width-01 ... OK
Check       I-RF_x0-01 ... OK
Check          I-SB-01 ... OK
Check          I-SH-01 ... OK
Check         I-SLL-01 ... OK
Check        I-SLLI-01 ... OK
Check         I-SLT-01 ... OK
Check        I-SLTI-01 ... OK
Check       I-SLTIU-01 ... OK
Check        I-SLTU-01 ... OK
Check         I-SRA-01 ... OK
Check        I-SRAI-01 ... OK
Check         I-SRL-01 ... OK
Check        I-SRLI-01 ... OK
Check         I-SUB-01 ... OK
Check          I-SW-01 ... OK
Check         I-XOR-01 ... OK
Check        I-XORI-01 ... OK
--------------------------------
OK: 48/48
```
The status "ignored" on four tests is intentionally, because without privilege mode no exepction handling is possible. The test will fail with an invalid opcode assertion and will not write a signature.

### Compliance suite technical details

The forked test suite contains the target `bonfire-core`. In the `device/rv32i` and `device/rv32Zicsr` subdirectory the target specific `Makefile.include` and the adapted header files are contained. The Makefile will call tb_run.py with the elf, hex and sig parameters as outlined above. Please refer to the Makefile for supported parameters. 

## Generating bonfire-core 
... todo

## (depreceated)  Simulation the Core with GHDL



    fusesoc --cores-root .  run --target=sim   bonfire-core --testfile=code/loadsave.hex


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

### Bonfire extended core

The extended core relies on an external dependeny - bonfire-library
You can install it locally with git clone and add it to the bonfire project

```
fusesoc library add  --sync-type=local  bonfire-library ../bonfire-library
```

```
usage: fusesoc library add [-h] [--sync-version SYNC-VERSION] [--location LOCATION] [--sync-type {git,local}] [--no-auto-sync] [--global]
                           [name] sync-uri

positional arguments:
  name                  A friendly name for the library. Defaults to last part of sync-uri if not specified.
  sync-uri              The URI source for the library (can be a file system path)

options:
  -h, --help            show this help message and exit
  --sync-version SYNC-VERSION
                        Optionally specify the version of the library to use, for providers that support it
  --location LOCATION   The location to store the library into (defaults to fusesoc_libraries/[name] or $XDG_DATA_HOME/[name] when --global is
                        set)
  --sync-type {git,local}
                        The provider type for the library. Defaults to 'git'.
  --no-auto-sync        Disable automatic updates of the library
  --global              Use the global FuseSoC config file in $XDG_CONFIG_HOME/fusesoc/fusesoc.conf
  ```
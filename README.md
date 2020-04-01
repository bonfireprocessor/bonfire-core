## A RISC-V Core in MyHDL

Bonfire Core is an modular, configurable RISC-V core written in MyHDL. 

### First milestone
The first design milestone is reached and passes the following goals:

* Implement rv32i subset without any privilege mode features (no CSRs, no interrupts, no traps). 
* Pass riscv-compliance suite in MyHDL based simulation except the tests which require on traps/ CSRs to work (I-EBREAK-01, I-ECALL-01, I-MISALIGN_JMP-01,I-MISALIGN_LDST-01  )
* Be able to run a simple test pogram written in C on a real FPGA
* Reach clock frequencies comparable to bonfire-cpu


This is of course not enough to have a fully usable CPU, but allows to check the feasbilty of the design. 

The FPGA implementation is not part of this project, it is part of the bonfire-basic-soc project, contained in an experimental "bonfire_core" branch. The implementation cuts a few corners, because the single purpose of it is to have a PoC running on an FPGA. The implementation was tested on a Digilent Arty A7 board and the Trion T8 based FireAnt board. 

### Prerequisites
* Python - Currently the code is tested with Python 2.7.12 and Python 3.5.2 - other versions may work

* MyHDL 0.11

* pyelftools - required for extracting the test signatures when running riscv-compliance suite

* RISC-V toolchain with support for rv32i (the default multilib setup contains it)

I think there are enough tutorials how to install all these tools (including the RISC-V toolchain) so I will not repeat it here. 

### Running tests

Currently bonfire-core does not use any test framework, like pyunit. There is a test runner tb_run.py which allows to run various tests. It has a very basic command line interface, which not really robust error handling. There are several classes of tests:

#### Module unit tests
They test a singe module. Most of the tests benches are self-checking and raise an assertion on error. A few (like the barrel shifter) just output the results, so they need visual inspection of correctness. Some tests (like tb_decoder) are very rudimentary at the moment and should be improved.
The module unit tests can be invoked with 

````
python tb_run.py --ut_modules
````

#### Load store unit tests
The load store unit tests can be invoked separatly and indpendant of the other unit tests. Reason is, that the loadstore module is quite complex, because it is already prepared to support a pipelined LSU, allowing back-to-back load/stores. It tests the LSU with different configurations and pipeline depths. 

The Load/Store unit tests can be invoked with 

````
python tb_run.py --ut_loadstore
````

#### Pipeline integration tests
Currently bonfire-core has only three stage pipeline implemented. It is separated into a backend and the fetch unit. The pipeline integration tests test the backend alone and together with the fetch unit. 

The Pipeline integration tests can be invoked with
````
python tb_run.py --ut_loadstore
````

### Core integration test
This test runs the complete bonfire-core in a test bench environment with 16KB of memory at address 0 and a monitor port at address range 0x10000000 - 0x1fffffff.

Writes to the monitor range will be reported to the console. In addition a write to monitor base address will stop the test bench.
Convention is that the test write an success (0x1) or error code (either 0 or -1 (0xffffffff) ) to the monitor base address.

Optionally the monitor can dump part of the memory as a signature to a file, this is used to support the riscv-compliance test suite.


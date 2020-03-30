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
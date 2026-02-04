# tb_run.py (legacy runner)

This document contains the legacy `tb_run.py` workflow and RISC-V compliance notes.

The main README focuses on the pytest-based workflow.

For an overview of the pytest test suite and how it maps to the legacy groups, see:
- [`tests/README.md`](tests/README.md)

### Legacy tb_run.py (still supported)
There are several classes of tests:

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

Compliance testing has been moved into a separate document:

- [`COMPLIANCE.md`](COMPLIANCE.md)

## Generating bonfire-core 
... todo

## (depreceated)  Simulation the Core with GHDL



    fusesoc --cores-root .  run --target=sim   bonfire-core --testfile=code/loadsave.hex

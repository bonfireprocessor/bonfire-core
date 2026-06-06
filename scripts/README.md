# `scripts/bonfire-core` — Universal runner

This repository uses **pytest** for unit + integration tests. The script
`bonfire-core/scripts/bonfire-core` is the recommended **single entry point**
for day-to-day development:

- activates the repo-local Python venv (`.venv/`) (unless you tell it not to)
- ensures the RISC-V toolchain is available on `PATH`
- runs selected pytest test groups (unit / pipeline / core HEX integration)
- can also run *exactly one* core program (`--hex ...`) with optional ELF / signature / VCD output
- can start the simulated GDB server (`--gdbserver [--port N]`)
- can start the OpenOCD remote_bitbang JTAG simulation server (`--openocd-bitbang [--port N]`)

Note: the script always runs core tests with normal pytest output capture. If you want to see the MyHDL/monitor prints, pass `-- -s` to pytest (or use `--hex`, which already runs with `-s`).

## Quick start

```bash
cd bonfire-core
scripts/bonfire-core --install
scripts/bonfire-core --all
```

## Usage

```text
scripts/bonfire-core [OPTIONS] [-- PYTEST_ARGS...]

Test selection:
  --ut              Run unit + pipeline integration tests (pytest-based)
  --integration     Run core HEX integration tests (pytest-based)
  --all             Run all tests (default when no args are given)
  --gdbserver       Start the simulated GDB server instead of running pytest
  --openocd-bitbang Start the OpenOCD remote_bitbang JTAG simulation server
  --port N          Server TCP port (GDB default: first free port in 5500-5550,
                    OpenOCD bitbang default: 3335)

Environment / venv:
  --install         Create/update ./.venv and install Python deps (scripts/install.sh)
  --keepenv         Do not activate ./.venv; keep current Python environment
                    (also via BONFIRE_CORE_KEEPENV=1)

Single core run (pytest-based):
  --hex PATH        Run exactly one HEX program via tests/test_core.py
                    With --gdbserver: HEX image to load (default: code/build/debug-tests/endless.hex)
  --elf PATH        Optional ELF path (override)
  --sig PATH        Optional signature output path (override)
  --vcd PATH        Optional VCD output path (MyHDL appends .vcd automatically)

Other:
  --help, -h        Show help

Notes:
- Any unknown options are passed through to pytest.
- Use "--" to pass arguments to pytest unmodified.
```

### OpenOCD remote_bitbang JTAG server

Start the simulated JTAG remote-bitbang server:

```bash
scripts/bonfire-core --openocd-bitbang --port 3335
```

The server runs until interrupted with Ctrl-C. In another terminal, OpenOCD can
connect through its `remote_bitbang` adapter. Minimal IDCODE / scan-chain config:

```tcl
adapter driver remote_bitbang
remote_bitbang host localhost
remote_bitbang port 3335
transport select jtag

jtag newtap bonfire cpu -irlen 5 -expected-id 0x10e31913

init
scan_chain
shutdown
```

Run it with:

```bash
openocd -f bonfire_remote_bitbang.cfg
```

This first prototype exposes the JTAG DTM enough for OpenOCD to read the TAP
IDCODE. It does not yet run a full Bonfire core debug session through OpenOCD.

## Common workflows

### Run everything

```bash
scripts/bonfire-core
# or explicitly
scripts/bonfire-core --all
```

Expected output (example):

```text
riscv64-unknown-elf-size  build/basic_alu.elf
   text    data     bss     dec     hex filename
    260       0       0     260     104 build/basic_alu.elf
riscv64-unknown-elf-size  build/simple_loop.elf
   text    data     bss     dec     hex filename
     56       0       0      56      38 build/simple_loop.elf
riscv64-unknown-elf-size  build/loop.elf
   text    data     bss     dec     hex filename
    112       0       0     112      70 build/loop.elf
riscv64-unknown-elf-size  build/loadsave.elf
   text    data     bss     dec     hex filename
    280       0       0     280     118 build/loadsave.elf
riscv64-unknown-elf-size  build/branch.elf
   text    data     bss     dec     hex filename
    168       0       0     168      a8 build/branch.elf
riscv64-unknown-elf-size  build/wb_test.elf
   text    data     bss     dec     hex filename
     68       0       0      68      44 build/wb_test.elf
riscv64-unknown-elf-size  build/csr.elf
   text    data     bss     dec     hex filename
    356       0       0     356     164 build/csr.elf
riscv64-unknown-elf-size  build/trap.elf
   text    data     bss     dec     hex filename
    136       0       0     136      88 build/trap.elf
................                                                         [100%]
16 passed in 0.82s
.......                                                                  [100%]
7 passed in 3.41s
```

### Unit + pipeline tests only

```bash
scripts/bonfire-core --ut -q
```

Expected output (example):

```text
................                                                         [100%]
```

### Core HEX integration tests

```bash
scripts/bonfire-core --integration -q
```

Expected output (example):

```text
riscv64-unknown-elf-size  build/basic_alu.elf
   text    data     bss     dec     hex filename
    260       0       0     260     104 build/basic_alu.elf
riscv64-unknown-elf-size  build/simple_loop.elf
   text    data     bss     dec     hex filename
     56       0       0      56      38 build/simple_loop.elf
riscv64-unknown-elf-size  build/loop.elf
   text    data     bss     dec     hex filename
    112       0       0     112      70 build/loop.elf
riscv64-unknown-elf-size  build/loadsave.elf
   text    data     bss     dec     hex filename
    280       0       0     280     118 build/loadsave.elf
riscv64-unknown-elf-size  build/branch.elf
   text    data     bss     dec     hex filename
    168       0       0     168      a8 build/branch.elf
riscv64-unknown-elf-size  build/wb_test.elf
   text    data     bss     dec     hex filename
     68       0       0      68      44 build/wb_test.elf
riscv64-unknown-elf-size  build/csr.elf
   text    data     bss     dec     hex filename
    356       0       0     356     164 build/csr.elf
riscv64-unknown-elf-size  build/trap.elf
   text    data     bss     dec     hex filename
    136       0       0     136      88 build/trap.elf
.......                                                                  [100%]
```

Run the full core HEX integration tests with full per-test output (`-vv`):

```bash
scripts/bonfire-core --integration -- -vv
```

Expected output (example):

```text
riscv64-unknown-elf-size  build/basic_alu.elf
   text	   data	    bss	    dec	    hex	filename
    260	      0	      0	    260	    104	build/basic_alu.elf
riscv64-unknown-elf-size  build/simple_loop.elf
   text	   data	    bss	    dec	    hex	filename
     56	      0	      0	     56	     38	build/simple_loop.elf
riscv64-unknown-elf-size  build/loop.elf
   text	   data	    bss	    dec	    hex	filename
    112	      0	      0	    112	     70	build/loop.elf
riscv64-unknown-elf-size  build/loadsave.elf
   text	   data	    bss	    dec	    hex	filename
    280	      0	      0	    280	    118	build/loadsave.elf
riscv64-unknown-elf-size  build/branch.elf
   text	   data	    bss	    dec	    hex	filename
    168	      0	      0	    168	     a8	build/branch.elf
riscv64-unknown-elf-size  build/wb_test.elf
   text	   data	    bss	    dec	    hex	filename
     68	      0	      0	     68	     44	build/wb_test.elf
riscv64-unknown-elf-size  build/csr.elf
   text	   data	    bss	    dec	    hex	filename
    356	      0	      0	    356	    164	build/csr.elf
riscv64-unknown-elf-size  build/trap.elf
   text	   data	    bss	    dec	    hex	filename
    136	      0	      0	    136	     88	build/trap.elf
============================= test session starts ==============================
platform linux -- Python 3.13.5, pytest-9.0.2, pluggy-1.6.0 -- /home/thomas/.openclaw/workspace/bonfire-core/.venv/bin/python
cachedir: .pytest_cache
rootdir: /home/thomas/.openclaw/workspace/bonfire-core
configfile: pytest.ini
collecting ... collected 7 items

tests/test_core.py::test_core[code/build/core-tests/basic_alu.hex] PASSED           [ 14%]
tests/test_core.py::test_core[code/build/core-tests/branch.hex] PASSED              [ 28%]
tests/test_core.py::test_core[code/build/core-tests/csr.hex] PASSED                 [ 42%]
tests/test_core.py::test_core[code/build/core-tests/loadsave.hex] PASSED            [ 57%]
tests/test_core.py::test_core[code/build/core-tests/loop.hex] PASSED                [ 71%]
tests/test_core.py::test_core[code/build/core-tests/simple_loop.hex] PASSED         [ 85%]
tests/test_core.py::test_core[code/build/core-tests/trap.hex] PASSED                [100%]

============================== 7 passed in 3.30s ===============================
```

Filter to one program (pytest `-k`):

```bash
scripts/bonfire-core --integration -- -k loadsave -vv
```

Expected output (example):

```text
riscv64-unknown-elf-size  build/basic_alu.elf
   text    data     bss     dec     hex filename
    260       0       0     260     104 build/basic_alu.elf
riscv64-unknown-elf-size  build/simple_loop.elf
   text    data     bss     dec     hex filename
     56       0       0      56      38 build/simple_loop.elf
riscv64-unknown-elf-size  build/loop.elf
   text    data     bss     dec     hex filename
    112       0       0     112      70 build/loop.elf
riscv64-unknown-elf-size  build/loadsave.elf
   text    data     bss     dec     hex filename
    280       0       0     280     118 build/loadsave.elf
riscv64-unknown-elf-size  build/branch.elf
   text    data     bss     dec     hex filename
    168       0       0     168      a8 build/branch.elf
riscv64-unknown-elf-size  build/wb_test.elf
   text    data     bss     dec     hex filename
     68       0       0      68      44 build/wb_test.elf
riscv64-unknown-elf-size  build/csr.elf
   text    data     bss     dec     hex filename
    356       0       0     356     164 build/csr.elf
riscv64-unknown-elf-size  build/trap.elf
   text    data     bss     dec     hex filename
    136       0       0     136      88 build/trap.elf
============================= test session starts ==============================
platform linux -- Python 3.13.5, pytest-9.0.2, pluggy-1.6.0 -- /home/thomas/.openclaw/workspace/bonfire-core/.venv/bin/python
cachedir: .pytest_cache
rootdir: /home/thomas/.openclaw/workspace/bonfire-core
configfile: pytest.ini
collecting ... collected 7 items / 6 deselected / 1 selected

tests/test_core.py::test_core[code/build/core-tests/loadsave.hex] PASSED            [100%]

======================= 1 passed, 6 deselected in 0.34s ========================
```

Show monitor output / prints (`-s`):

```bash
scripts/bonfire-core --integration -- -s -vv
```

(Expect additional MyHDL monitor output between the pytest lines.)

### Start the simulated GDB server

The runner can start the Bonfire simulation together with the built-in GDB remote server.
This is useful when you want to connect a real `gdb` or `gdb-multiarch` session to the simulated core.

Default start:

```bash
scripts/bonfire-core --gdbserver
```

This will:

- build `code/build/debug-tests/endless.hex` if needed
- start the simulation
- open a TCP listener for GDB remote protocol connections
- choose the first free port in `5500-5550`

Choose an explicit port:

```bash
scripts/bonfire-core --gdbserver --port 1234
```

Use a different HEX image:

```bash
scripts/bonfire-core --gdbserver --hex code/build/debug-tests/endless.hex --port 1234
```

You can also start the module directly without the shell wrapper:

```bash
python -m gdbserver --hex code/build/debug-tests/endless.hex --port 1234
```

#### Connecting with `gdb-multiarch`

Open a second terminal and start GDB with the matching ELF file:

```bash
gdb-multiarch code/build/debug-tests/endless.elf
```

Inside GDB, set the architecture to 32-bit RISC-V and connect to the remote target:

```gdb
set architecture riscv:rv32
target remote localhost:5500
```

A complete example session looks like this:

```text
gdb-multiarch code/build/debug-tests/endless.elf
GNU gdb (Debian 16.3-1) 16.3
Copyright (C) 2024 Free Software Foundation, Inc.
License GPLv3+: GNU GPL version 3 or later <http://gnu.org/licenses/gpl.html>
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.
Type "show copying" and "show warranty" for details.
This GDB was configured as "x86_64-linux-gnu".
Type "show configuration" for configuration details.
For bug reporting instructions, please see:
<https://www.gnu.org/software/gdb/bugs/>.
Find the GDB manual and other documentation resources online at:
 <http://www.gnu.org/software/gdb/documentation/>.

For help, type "help".
Type "apropos word" to search for commands related to "word"...
Reading symbols from code/build/debug-tests/endless.elf...
(gdb) set architecture riscv:rv32
The target architecture is set to "riscv:rv32".
(gdb) target remote localhost:5500
Remote debugging using localhost:5500
loop () at debug-tests/endless.S:12
12 sw t2, (t0)
(gdb) x counter
0x20 <counter>: 0x000010fe
(gdb) cont
Continuing.
^C
Program received signal SIGTRAP, Trace/breakpoint trap.
loop () at debug-tests/endless.S:10
10 lw t2, (t0)
(gdb) x counter
0x20 <counter>: 0x000012c4
(gdb) disassemble
Dump of assembler code for function loop:
=> 0x00000010 <+0>: lw t2,0(t0)
 0x00000014 <+4>: addi t2,t2,1
 0x00000018 <+8>: sw t2,0(t0)
 0x0000001c <+12>: j 0x10 <loop>
End of assembler dump.
(gdb) info registers
ra 0x0 0x0 <_start>
sp 0x0 0x0 <_start>
gp 0x0 0x0 <_start>
tp 0x0 0x0 <_start>
t0 0x20 32
t1 0xdeadbeef -559038737
t2 0x12c4 4804
fp 0x0 0x0 <_start>
s1 0x0 0
a0 0x0 0
a1 0x0 0
a2 0x0 0
a3 0x0 0
a4 0x0 0
a5 0x0 0
a6 0x0 0
a7 0x0 0
s2 0x0 0
s3 0x0 0
s4 0x0 0
s5 0x0 0
s6 0x0 0
s7 0x0 0
s8 0x0 0
s9 0x0 0
s10 0x0 0
s11 0x0 0
t3 0x0 0
t4 0x0 0
t5 0x0 0
t6 0x0 0
pc 0x10 0x10 <loop>
(gdb)
```

#### Typical workflow

1. Start the server:

   ```bash
   scripts/bonfire-core --gdbserver --port 5500
   ```

2. In a second terminal, open GDB:

   ```bash
   gdb-multiarch code/build/debug-tests/endless.elf
   ```

3. In GDB:

   ```gdb
   set architecture riscv:rv32
   target remote localhost:5500
   ```

4. Inspect state and continue execution:

   ```gdb
   info registers
   disassemble
   cont
   ```

5. Interrupt execution with `Ctrl-C` inside GDB to get back to the loop body.

#### Useful GDB commands

```gdb
show architecture
info registers
disassemble
x counter
x/4wx 0x20
display/i $pc
si
ni
cont
```

Notes:

- The `.hex` file is loaded into the simulated RAM.
- The `.elf` file is used by GDB for symbols and disassembly.
- For `gdb-multiarch`, `set architecture riscv:rv32` is typically required before `target remote`.
- `Ctrl-C` in GDB sends a remote break and should stop the simulated core cleanly.

### Run a single HEX program (single-run mode)

```bash
scripts/bonfire-core --hex code/build/core-tests/loadsave.hex
```

Expected output (example):

```text
============================= test session starts ==============================
platform linux -- Python 3.13.5, pytest-9.0.2, pluggy-1.6.0
rootdir: /home/thomas/.openclaw/workspace/bonfire-core
configfile: pytest.ini
collected 1 item

tests/test_core.py eof at adr:0x118
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
.

============================== 1 passed in 0.35s ===============================
```

With VCD output (file name base, MyHDL will append `.vcd`):

```bash
scripts/bonfire-core --hex code/build/core-tests/loadsave.hex --vcd /tmp/loadsave.vcd
```

VCD also works for integration tests (it traces all *selected* test cases, so combine it with `-k`):

```bash
scripts/bonfire-core --integration --vcd /tmp/loadsave.vcd -- -k loadsave -q
```

## Environment variables

### Toolchain

- `TOOLCHAIN_BIN` (default: `$HOME/opt/riscv-gnu-toolchain/bin`)
- `TARGET_PREFIX` (default: `riscv64-unknown-elf`)

`TARGET_PREFIX` can be either:

- a plain prefix, e.g. `riscv64-unknown-elf`
- **or** a full path prefix, e.g. `/opt/riscv/bin/riscv64-unknown-elf`

### Test artifacts

- `BONFIRE_CORE_HEX_DIR` (default: `code/build/core-tests`) — where integration-test `.hex` files are discovered
- `BONFIRE_ELF_DIR` (default: `code/build/core-tests`) — where built `.elf` files are expected
- `BONFIRE_SIG_DIR` (default: `signatures`) — where signature files are written/collected

### Keep current Python environment

- `BONFIRE_CORE_KEEPENV=1` is equivalent to `--keepenv`

## GDB server notes

- `--gdbserver` is a separate mode and cannot be combined with `--ut`, `--integration`, or pytest pass-through args.
- In `--gdbserver` mode, only `--hex` and `--port` are accepted from the run-specific options.

## Exit codes

- exits non-zero on missing toolchain / missing venv (unless `--keepenv`) / failing tests

# `scripts/bonfire-core` — Universal runner

This repository uses **pytest** for unit + integration tests. The script
`bonfire-core/scripts/bonfire-core` is the recommended **single entry point**
for day-to-day development:

- activates the repo-local Python venv (`.venv/`) (unless you tell it not to)
- ensures the RISC-V toolchain is available on `PATH`
- runs selected pytest test groups (unit / pipeline / core HEX integration)
- can also run *exactly one* core program (`--hex ...`) with optional ELF / signature / VCD output

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

Environment / venv:
  --install         Create/update ./.venv and install Python deps (scripts/install.sh)
  --keepenv         Do not activate ./.venv; keep current Python environment
                    (also via BONFIRE_CORE_KEEPENV=1)

Single core run (pytest-based):
  --hex PATH        Run exactly one HEX program via tests/test_core.py
  --elf PATH        Optional ELF path (override)
  --sig PATH        Optional signature output path (override)
  --vcd PATH        Optional VCD output path (MyHDL appends .vcd automatically)

Other:
  --help, -h        Show help

Notes:
- Any unknown options are passed through to pytest.
- Use "--" to pass arguments to pytest unmodified.
```

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

tests/test_core.py::test_core[code/build/basic_alu.hex] PASSED           [ 14%]
tests/test_core.py::test_core[code/build/branch.hex] PASSED              [ 28%]
tests/test_core.py::test_core[code/build/csr.hex] PASSED                 [ 42%]
tests/test_core.py::test_core[code/build/loadsave.hex] PASSED            [ 57%]
tests/test_core.py::test_core[code/build/loop.hex] PASSED                [ 71%]
tests/test_core.py::test_core[code/build/simple_loop.hex] PASSED         [ 85%]
tests/test_core.py::test_core[code/build/trap.hex] PASSED                [100%]

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

tests/test_core.py::test_core[code/build/loadsave.hex] PASSED            [100%]

======================= 1 passed, 6 deselected in 0.34s ========================
```

Show monitor output / prints (`-s`):

```bash
scripts/bonfire-core --integration -- -s -vv
```

(Expect additional MyHDL monitor output between the pytest lines.)

### Run a single HEX program (single-run mode)

```bash
scripts/bonfire-core --hex code/build/loadsave.hex
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
scripts/bonfire-core --hex code/build/loadsave.hex --vcd /tmp/loadsave.vcd
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

- `BONFIRE_ELF_DIR` (default: `code/build`) — where built `.elf` files are expected
- `BONFIRE_SIG_DIR` (default: `signatures`) — where signature files are written/collected

### Keep current Python environment

- `BONFIRE_CORE_KEEPENV=1` is equivalent to `--keepenv`

## Exit codes

- exits non-zero on missing toolchain / missing venv (unless `--keepenv`) / failing tests

# Core Test Programs

The `code/` tree contains small RISC-V assembly test programs used by the
core integration tests.

## Building

Build all core and SoC programs:

```bash
cd bonfire-core/code
make clean
make all TARGET_PREFIX=riscv64-unknown-elf KEEP_ELF=1
```

Or from the repo root:

```bash
make -C code clean all TARGET_PREFIX=riscv64-unknown-elf KEEP_ELF=1
```

## Artifacts

Programs are built into `code/build/core-tests/`:

| Extension | Contents |
| --- | --- |
| `*.hex` | Text hexdump of 32-bit words (one word per line); loaded by `tb_core`. |
| `*.elf` | ELF binary; used for symbol extraction and debugging. |
| `*.lst` | Interleaved disassembly listing. |
| `*.sym` | Symbol dump. |

## Monitor port convention

Most programs communicate success or failure through the testbench **monitor
port**:

| Address | Meaning |
| --- | --- |
| `monitor + 0` (`0x10000000`) | Write `1` for success, write `0xffffffff` for failure |
| `monitor + 4` | Optional: additional diagnostics |
| `monitor + 0x200` | Optional: result log area |

A write to `monitor + 0` also terminates the testbench run.

## Programs

### `basic_alu.S`

Self-checking ALU/shift/branch sanity test plus a small byte load/store check.
Writes expected values to the result log area and fails fast on mismatch.

### `simple_loop.S`

Minimal countdown loop and final success write to the monitor base.

### `loop.S`

Loop and forward branch test plus `jalr` call/return test. Signals success by
writing `1` to the monitor base.

### `loadsave.S`

Focused load/store test covering:

- `sw` / `lw`
- `sb` / `lbu` / `lb`
- `sh` / `lhu` / `lh`
- negative offsets

### `branch.S`

Branch instruction tests: `beq`, `bne`, `blt`, `bge`, `bltu`, `bgeu`.
On failure writes `0xffffffff` to the monitor base.

### `csr.S`

CSR instruction tests (uses `core-tests/encoding.h`). Validates CSR read/write
and some fixed CSR values.

### `trap.S`

Simple trap / `ecall` test using `mtvec` + `mret`.

### `wb_test.S`

Wishbone test program. Expects a Wishbone BFM / external target at `wb_base`.

!!! note
    `wb_test` is intentionally **skipped** by the normal core integration
    tests (`tests/test_core.py`).

## Running a single program

Via pytest:

```bash
pytest -s -vv tests/test_core.py -k loadsave
pytest -s -vv tests/test_core.py -k "code/build/core-tests/loadsave.hex"
```

Via the universal runner:

```bash
scripts/bonfire-core --hex code/build/core-tests/loadsave.hex
```

# Test programs (`code/`)

This directory contains small RISC-V test programs used by the **core integration tests**.

They are written in assembly (`*.S`) and built into artifacts under `code/build/`:
- `*.elf` (for symbol extraction / debugging)
- `*.hex` (text hexdump of 32-bit words, loaded by `tb_core`)
- `*.lst` / `*.sym` (objdump outputs)

Build all programs:
```bash
cd bonfire-core/code
make clean
make all TARGET_PREFIX=riscv64-unknown-elf KEEP_ELF=1
```

## Monitor convention
Most programs use the bonfire-core testbench **monitor port**:
- base address: `monitor` symbol (mapped to `0x10000000` in the testbench)
- **success**: write `1` to `monitor + 0`
- **failure**: write `-1` (`0xffffffff`) to `monitor + 0`
- some tests also write additional diagnostics to `monitor + 4` and/or `monitor + 0x200` (result log area)

## Programs

### `basic_alu.S`
Self-checking ALU/shift/branch sanity + a small byte load/store check.
Writes expected values to a result log area and fails fast on mismatch.

### `simple_loop.S`
Minimal countdown loop and final success write to the monitor base.

### `loop.S`
Loop + forward branch test + `jalr` call/return test.
Signals success by writing `1` to the monitor base.

### `loadsave.S`
Focused load/store test covering:
- `sw/lw`
- `sb/lbu/lb`
- `sh/lhu/lh`
- negative offsets

(Contains commented-out misalignment experiments.)

### `branch.S`
Branch instruction tests (`beq/bne/blt/bge/bltu/bgeu`).
On failure writes `-1` to the monitor base.

### `csr.S`
CSR instruction tests (uses `encoding.h`).
Intended to validate CSR read/write and some fixed CSR values.

### `trap.S`
Simple trap/`ecall` test using `mtvec` + `mret`.

### `wb_test.S`
Wishbone test program (special case).

Note: `wb_test` is intentionally **skipped** by the normal core integration tests (`tests/test_core.py`), because it expects a Wishbone BFM / external target (`wb_base`).

## How to run a single program in the core integration test
From repo root:

```bash
pytest -s -vv tests/test_core.py -k loadsave
# or exact id
pytest -s -vv tests/test_core.py -k "code/build/loadsave.hex"
```

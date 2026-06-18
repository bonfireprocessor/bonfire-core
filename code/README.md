# Test programs (`code/`)

This directory contains small RISC-V test programs used by the **core integration tests**.

They are written in assembly (`core-tests/*.S`) and built into artifacts under
`code/build/core-tests/`:
- `*.elf` (for symbol extraction / debugging)
- `*.hex` (text hexdump of 32-bit words, loaded by `tb_core`)
- `*.lst` / `*.sym` (objdump outputs)

Build all core and SoC test programs:
```bash
cd bonfire-core/code
make clean
make all TARGET_PREFIX=riscv64-unknown-elf KEEP_ELF=1
```

## SoC LED programs

Small C programs for the MyHDL SoC live under `soc/apps/`:

- `soc/apps/led/main.c`: LED counter smoke test.
- `soc/apps/wishbone/main.c`: Wishbone bridge smoke test that reports success
  through the LED register.
- `soc/apps/hello/main.c`: Extended SoC UART/GPIO smoke test used by the VHDL
  Extended SoC simulation.
- `soc/apps/monitor/main.c`: minimal interactive UART monitor with `I` info
  and `D [addr]` memory dump commands.
- `soc/apps/uart_echo/main.c`: native UART TX/RX echo integration test used by
  the MyHDL and converted-VHDL SoC testbenches.

They use the local platform headers in `soc/platforms/` and do not depend on
the external `bonfire-software` repository.
Shared minimal runtime helpers live under `soc/runtime/`; currently this is a
small UART console wrapper plus a compact `snprintf`/`printk` implementation
for test output without pulling in a full C runtime.
Each platform also has a matching linker script in `soc/linker/` for board-
specific RAM origin and size.
The platform header controls the visible blink speed through
`BONFIRE_LED_SHIFT`; the simulation platform uses shift `0`.

Build one SoC program:

```bash
make soc SOC_APP=led SOC_PLATFORM=sim TARGET_PREFIX=riscv64-unknown-elf
make soc SOC_APP=wishbone SOC_PLATFORM=sim TARGET_PREFIX=riscv64-unknown-elf
make soc SOC_APP=hello SOC_PLATFORM=sim TARGET_PREFIX=riscv64-unknown-elf
make soc SOC_APP=monitor SOC_PLATFORM=sim TARGET_PREFIX=riscv64-unknown-elf
make soc SOC_APP=led SOC_PLATFORM=icepizero TARGET_PREFIX=riscv64-unknown-elf
```

Build only the currently defined SoC firmware variants:

```bash
make soc-all TARGET_PREFIX=riscv64-unknown-elf
```

Generated artifacts are written below `code/build/soc/<platform>/`.

## Monitor convention
Most programs use the bonfire-core testbench **monitor port**:
- base address: `monitor` symbol (mapped to `0x10000000` in the testbench)
- **success**: write `1` to `monitor + 0`
- **failure**: write `-1` (`0xffffffff`) to `monitor + 0`
- some tests also write additional diagnostics to `monitor + 4` and/or `monitor + 0x200` (result log area)

## Programs

### `core-tests/basic_alu.S`
Self-checking ALU/shift/branch sanity + a small byte load/store check.
Writes expected values to a result log area and fails fast on mismatch.

### `core-tests/simple_loop.S`
Minimal countdown loop and final success write to the monitor base.

### `core-tests/loop.S`
Loop + forward branch test + `jalr` call/return test.
Signals success by writing `1` to the monitor base.

### `core-tests/loadsave.S`
Focused load/store test covering:
- `sw/lw`
- `sb/lbu/lb`
- `sh/lhu/lh`
- negative offsets

(Contains commented-out misalignment experiments.)

### `core-tests/branch.S`
Branch instruction tests (`beq/bne/blt/bge/bltu/bgeu`).
On failure writes `-1` to the monitor base.

### `core-tests/csr.S`
CSR instruction tests (uses `core-tests/encoding.h`).
Intended to validate CSR read/write and some fixed CSR values.

### `core-tests/trap.S`
Simple trap/`ecall` test using `mtvec` + `mret`.

### `core-tests/wb_test.S`
Wishbone test program (special case).

Note: `wb_test` is intentionally **skipped** by the normal core integration tests (`tests/test_core.py`), because it expects a Wishbone BFM / external target (`wb_base`).

## How to run a single program in the core integration test
From repo root:

```bash
pytest -s -vv tests/test_core.py -k loadsave
# or exact id
pytest -s -vv tests/test_core.py -k "code/build/core-tests/loadsave.hex"
```

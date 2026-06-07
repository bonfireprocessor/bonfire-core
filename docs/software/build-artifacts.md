# Build Artifacts

This page summarizes the generated software outputs and where to find them.

## Building everything

From the repository root:

```bash
make -C code clean all TARGET_PREFIX=riscv64-unknown-elf KEEP_ELF=1
```

Or step by step:

```bash
cd bonfire-core/code
make clean
make all TARGET_PREFIX=riscv64-unknown-elf KEEP_ELF=1
```

## Core test artifacts

Built into `code/build/core-tests/`:

| Extension | Contents |
| --- | --- |
| `*.hex` | Text hexdump (one 32-bit word per line); loaded by `tb_core`. |
| `*.elf` | ELF binary; used for symbol extraction and debugging. |
| `*.lst` | Interleaved disassembly listing. |
| `*.sym` | Symbol dump. |

## SoC firmware artifacts

Built into `code/build/soc/<platform>/`:

| Extension | Contents |
| --- | --- |
| `*.hex` | Text hexdump; loaded into SoC BRAM. |
| `*.elf` | ELF binary (when `KEEP_ELF=1`). |

### Simulation platform paths

| Path | Firmware |
| --- | --- |
| `code/build/soc/sim/led.hex` | LED counter smoke test |
| `code/build/soc/sim/wishbone.hex` | Wishbone bridge smoke test |
| `code/build/soc/sim/hello.hex` | Extended SoC UART/GPIO smoke test |
| `code/build/soc/sim/monitor.hex` | Interactive UART monitor |

## Debug test artifacts

Built into `code/build/debug-tests/`:

| Path | Contents |
| --- | --- |
| `code/build/debug-tests/endless.hex` | Endless loop program for GDB server testing |
| `code/build/debug-tests/endless.elf` | ELF binary for the above |

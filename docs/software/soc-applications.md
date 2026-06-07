# SoC Applications

The `code/soc/apps/` directory contains small C programs for the MyHDL SoC
simulation and FPGA smoke testing.

## Applications

| Application | Source | Description |
| --- | --- | --- |
| `led` | `soc/apps/led/main.c` | LED counter smoke test. Writes an incrementing counter to the LED register. |
| `wishbone` | `soc/apps/wishbone/main.c` | Wishbone bridge smoke test. Writes and reads the Wishbone bridge, reports success through the LED register. |
| `hello` | `soc/apps/hello/main.c` | Extended SoC UART/GPIO smoke test used by the VHDL Extended SoC simulation. Outputs text to UART0 and terminates with the stop marker byte `0x1A`. |
| `monitor` | `soc/apps/monitor/main.c` | Minimal interactive UART monitor with `I` (info) and `D [addr]` (memory dump) commands. |

## Supporting infrastructure

| Path | Description |
| --- | --- |
| `code/soc/runtime/` | Minimal runtime helpers: UART console wrapper, compact `snprintf` / `printk`. |
| `code/soc/platforms/` | Per-board platform headers; control `BONFIRE_LED_SHIFT` and board-specific constants. |
| `code/soc/linker/` | Per-board linker scripts for RAM origin and size. |

The platform header controls the visible LED blink speed through
`BONFIRE_LED_SHIFT`; the simulation platform uses shift `0`, FPGA board
profiles use larger shifts.

## Building

Build a single application:

```bash
make -C code soc SOC_APP=led SOC_PLATFORM=sim TARGET_PREFIX=riscv64-unknown-elf
make -C code soc SOC_APP=wishbone SOC_PLATFORM=sim TARGET_PREFIX=riscv64-unknown-elf
make -C code soc SOC_APP=hello SOC_PLATFORM=sim TARGET_PREFIX=riscv64-unknown-elf
make -C code soc SOC_APP=monitor SOC_PLATFORM=sim TARGET_PREFIX=riscv64-unknown-elf
```

Build for an FPGA board profile:

```bash
make -C code soc SOC_APP=led SOC_PLATFORM=icepizero TARGET_PREFIX=riscv64-unknown-elf
make -C code soc SOC_APP=hello SOC_PLATFORM=ulx3s TARGET_PREFIX=riscv64-unknown-elf
```

Build all defined SoC firmware variants:

```bash
make -C code soc-all TARGET_PREFIX=riscv64-unknown-elf
```

## Build artifacts

Generated files are written below `code/build/soc/<platform>/`.

Example for the simulation platform:

```text
code/build/soc/sim/led.hex
code/build/soc/sim/wishbone.hex
code/build/soc/sim/hello.hex
code/build/soc/sim/monitor.hex
```

## Running in the MyHDL testbench

The SoC integration tests exercise the LED and Wishbone firmware:

```bash
pytest -vv tests/test_soc_myhdl.py
```

The legacy runner:

```bash
python tb_run.py --new_soc --hex=code/build/soc/sim/led.hex
```

## Running in the Extended SoC (VHDL testbench)

The Extended SoC VHDL simulation uses `hello.hex`:

```bash
make -C code soc SOC_APP=hello SOC_PLATFORM=sim TARGET_PREFIX=riscv64-unknown-elf
fusesoc run --target=sim_extended ::bonfire-core-soc:0
```

Or via pytest:

```bash
pytest -vv tests/test_extended_soc_fusesoc.py
```

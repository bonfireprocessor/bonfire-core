# Bonfire Core SoC

This document describes the current System-on-Chip wrapper implemented in
`rtl/soc/bonfire_core_soc.py`. The SoC is still a work in progress. At the MyHDL
level it currently provides the CPU core, internal block RAM, a small LED
register, reset handling, and a Wishbone bridge. UART/GPIO/SPI integration is
not complete in the MyHDL SoC itself.

## Purpose

`BonfireCoreSoC` is the integration layer around the Bonfire RV32I CPU core. It
connects the core instruction and data buses to:

- dual-port block RAM used for code and data,
- a native DBus peripheral slot currently used by the LED register,
- a Wishbone master interface for external or wrapped peripherals.

The default reset address is `0xc0000000`, matching the block RAM address
window.

## Main Files

- `rtl/soc/bonfire_core_soc.py`: MyHDL SoC top-level generator.
- `rtl/uncore/bonfire_core_ex.py`: connects the CPU core to BRAM, native DBus, and
  Wishbone via the DBus interconnect.
- `rtl/uncore/dbus_interconnect.py`: simple 1-master/3-slave DBus address decoder.
- `rtl/uncore/ram_dp.py`: dual-port RAM implementations.
- `fusesoc-cores/templates/soc_top.vhd`: optional generated VHDL wrapper around
  the MyHDL SoC.
- `fusesoc-cores/generators/gen_soc.py`: FuseSoC generator entry point for SoC VHDL
  conversion.

## Top-Level Structure

The MyHDL top-level is:

```python
BonfireCoreSoC.bonfire_core_soc(
    sysclk,
    resetn,
    uart0_tx,
    uart0_rx,
    led,
    o_resetn,
    i_locked,
    wb_master=None,
)
```

It instantiates these blocks:

- `bonfireCoreExtendedInterface`: CPU core plus bus interconnect.
- `DualportedRamLaned` or `DualportedRam`: instruction/data memory.
- `led_out`: native DBus LED register.
- `wishbone_dummy`: dummy Wishbone target when no external Wishbone is exposed.
- `uart_dummy`: UART loopback placeholder.
- `reset_logic` or `no_reset_logic`: reset generation.

The CPU core itself is instantiated by `BonfireCoreTop.createInstance()` inside
`rtl/uncore/bonfire_core_ex.py`.

## Address Map

Address decoding uses bits `[31:28]` of the CPU data address.

| Region | Mask | Address range | Target |
| --- | ---: | --- | --- |
| Wishbone | `0x4` | `0x40000000` - `0x4fffffff` | Wishbone bridge |
| Native DBus | `0x8` | `0x80000000` - `0x8fffffff` | LED register |
| BRAM | `0xc` | `0xc0000000` - `0xcfffffff` | data RAM port |

The instruction bus is connected directly to the read-only RAM port. The data
bus reaches the RAM through the interconnect at the BRAM address window.

Addresses not matching one of these three windows return a DBus error.

## Memory

The SoC uses a dual-port RAM:

- port A: instruction fetch, read-only,
- port B: CPU data access, read/write.

The RAM is initialized from the `hexfile` passed to `BonfireCoreSoC`. The
default RAM address width is 11 words, i.e. `2**11` 32-bit words or 8 KiB.
FuseSoC targets can override this with `bram_adr_width`.

Two RAM implementations exist:

- `DualportedRamLaned`: four independent 8-bit lanes, default.
- `DualportedRam`: one 32-bit-wide memory.

`LanedMemory=True` is the default and is usually the better fit for byte-enable
writes.

## LED Register

The LED register is currently the only native MyHDL MMIO peripheral.

It is mapped through the native DBus window at `0x80000000` and responds to any
address selected by that top-nibble decode. The implementation does not decode
lower address bits.

Behavior:

- writes update the LED register when `dbus.we_o[0]` is set,
- reads return the current LED register value in the low LED bits,
- `ack_i` follows `en_o`,
- `stall_i` is always false.

`numLeds` must be between 1 and 8. If `ledActiveLow` is true, the output pins are
inverted.

## Wishbone Bridge

The CPU native DBus is converted to a Wishbone master by `DbusToWishbone()`.
The Wishbone address is word-addressed: DBus address bits `[31:2]` become the
Wishbone address.

When `exposeWishboneMaster=False`, the MyHDL SoC instantiates
`wishbone_dummy`. The dummy target:

- accepts every Wishbone cycle immediately,
- stores writes in a single 32-bit register,
- returns that register on reads,
- initializes to `0xdeadbeef`.

When `exposeWishboneMaster=True`, the Wishbone master bundle is exposed through
the generated MyHDL/VHDL top-level and no dummy is instantiated. This mode is
used by the extended VHDL wrapper.

## UART Status

The MyHDL SoC does not implement a real UART yet.

`uart_dummy()` currently connects:

```python
uart_tx = uart_rx
```

This is only a loopback placeholder. Software cannot yet use this MyHDL UART as
a real serial peripheral.

For extended SoC generation, `gen_soc.py` can wrap the MyHDL core with
`fusesoc-cores/templates/soc_top.vhd`. That VHDL wrapper exposes the MyHDL
Wishbone master to external VHDL peripherals. Depending on the `INST_UART_ONLY`
generic it instantiates
either:

- `zpuino_uart`, or
- `bonfire_soc_io`, which is intended to provide UART/GPIO/SPI functionality.

This wrapper path is separate from the `uart_dummy()` placeholder in
`bonfire_core_soc.py`.

## Reset Logic

The normal reset path is synchronous to `sysclk`:

- `resetn` is the active-low external reset input,
- `i_locked` is the PLL lock input,
- internal reset is asserted when `resetn` is low or `i_locked` is false,
- reset is passed through two flip-flops before reaching the logic.

`o_resetn` is currently driven high through a dummy signal in normal mode.

If `NoReset=True`, `no_reset_logic()` is used instead. It drives internal reset
inactive and `o_resetn` high. This is mainly useful for special conversion or
test scenarios.

## Configuration

`BonfireCoreSoC` accepts a `soc_config` dictionary. Common keys are:

| Key | Default | Meaning |
| --- | --- | --- |
| `resetAdr` | `0xc0000000` | CPU reset address |
| `bramAdrWidth` | `11` | RAM depth as address width in 32-bit words |
| `NoReset` | `False` | disable normal reset generation |
| `LanedMemory` | `True` | use byte-laned RAM implementation |
| `numLeds` | `4` | LED output width |
| `ledActiveLow` | `True` | invert LED output pins |
| `UseVHDLMemory` | `False` | currently unused |
| `exposeWishboneMaster` | `False` | expose Wishbone instead of using dummy |

FuseSoC parameters in `fusesoc-cores/bonfire-core-soc.core` are translated to
these keys by `gen_soc.py`.

## FuseSoC Generation

The SoC is generated through `gen_soc.py`.

Important FuseSoC parameters include:

- `hexfile`: RAM initialization file,
- `bram_adr_width`: RAM size,
- `laned_memory`: select lane-based RAM,
- `num_leds`: LED vector width,
- `led_active_low`: LED polarity,
- `extended_soc`: generate the VHDL wrapper around the MyHDL SoC,
- `expose_wishbone_master`: expose the Wishbone master directly.

When `extended_soc` is true, `gen_soc.py` forces `exposeWishboneMaster=True` so
that `fusesoc-cores/templates/soc_top.vhd` can attach VHDL peripherals to the
Wishbone bus.

## Firmware Smoke Tests

The repository contains small SoC smoke-test programs under `code/soc/apps`:

- `led`: writes an incrementing counter to the LED register.
- `wishbone`: writes and reads the Wishbone bridge, then reports success through
  the LED register.

The platform header selects the visible blink speed with `BONFIRE_LED_SHIFT`.
The simulation platform uses shift `0`; FPGA board profiles use larger shifts.

Build examples:

```bash
make -C code soc SOC_APP=led SOC_PLATFORM=sim TARGET_PREFIX=riscv64-unknown-elf
make -C code soc SOC_APP=wishbone SOC_PLATFORM=sim TARGET_PREFIX=riscv64-unknown-elf
make -C code soc SOC_APP=led SOC_PLATFORM=icepizero TARGET_PREFIX=riscv64-unknown-elf
make -C code soc-all TARGET_PREFIX=riscv64-unknown-elf
```

The generated HEX files are written below `code/build/soc/<platform>/`. The
FuseSoC SoC targets in `fusesoc-cores/bonfire-core-soc.core` reference these
local HEX files instead of the older external `bonfire-software` paths.
Board-specific constants live in `code/soc/platforms`, and matching RAM layouts
live in `code/soc/linker`.

## MyHDL Testbench

The pure MyHDL testbench lives in `tb/soc/bonfire_core_soc_tb.py`. It can run the
SoC in two modes:

- internal Wishbone dummy, used by the LED firmware test,
- exposed Wishbone master connected to `Wishbone_bfm`, used by the Wishbone
  bridge firmware test.

The older `uncore/tb_soc.py` testbench for `bonfireCoreExtendedInterface` has
been removed; `bonfireCoreExtendedInterface` remains an implementation block
used by `BonfireCoreSoC`.

## Current Limitations

- UART is not implemented in the MyHDL SoC; only a loopback dummy exists.
- The LED register is the only native MyHDL peripheral.
- The LED register uses only the top-nibble DBus decode and ignores lower
  address bits.
- `UseVHDLMemory` is present but unused.
- Interrupt handling is not wired at the SoC level.
- The external VHDL wrapper contains the more complete I/O direction, but this
  is not yet unified with the MyHDL SoC model.
- The Wishbone dummy is useful for bring-up, but it is not a real peripheral
  subsystem.

## Suggested Next Steps

1. Define a precise MMIO map for LED, UART, GPIO, SPI, timer, and interrupt
   controller.
2. Replace `uart_dummy()` with a real UART DBus or Wishbone peripheral.
3. Decide whether peripherals should live primarily in MyHDL, VHDL, or behind a
   stable Wishbone boundary.
4. Add lower-address decoding for native DBus peripherals.
5. Document software-visible register layouts once the MMIO map is stable.
6. Add integration tests that exercise SoC MMIO from RISC-V software.

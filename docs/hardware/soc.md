# SoC

This page documents the SoC-level wrappers around the Bonfire Core: the
integration block `bonfireCoreExtendedInterface` and the full SoC top-level
`BonfireCoreSoC`.

---

## `bonfireCoreExtendedInterface` (`bonfire_core_extended`)

Defined in `rtl/uncore/bonfire_core_ex.py`, `bonfireCoreExtendedInterface` is
the integration layer that connects the CPU core to memory and the bus
infrastructure. It is used internally by `BonfireCoreSoC` and can also be
instantiated directly.

### Purpose

`bonfireCoreExtendedInterface` connects:

- the Bonfire CPU core (via `BonfireCoreTop.createInstance()`),
- a dual-port block RAM (instruction port A, data port B),
- a native DBus peripheral slot,
- a Wishbone master bridge.

Address decoding uses an `AdrMask` on the CPU data address bits `[31:28]`
(configurable).

### Signature

```python
@block
def bonfireCoreExtendedInterface(
    wb_master: Wishbone_master_bundle,  # Wishbone master — default at 0x40000000
    db_master: DbusBundle,              # native DBus peripheral — default at 0x80000000
    bram_a:    RamPort32,               # BRAM instruction port (read-only)
    bram_b:    RamPort32,               # BRAM data port (read/write)
    clock:     BitSignal,
    reset:     BitSignal,
    config:    BonfireConfig = ...,
    wb_mask:   AdrMask = AdrMask(32, 28, 0x4),   # Wishbone window
    db_mask:   AdrMask = AdrMask(32, 28, 0x8),   # native DBus window
    bram_mask: AdrMask = AdrMask(32, 28, 0xc),   # BRAM window
)
```

### Ports

| Port | Type | Description |
| --- | --- | --- |
| `wb_master` | `Wishbone_master_bundle` | Wishbone B4 master exposed to the outside. The Wishbone address is word-addressed (DBus bits `[31:2]`). |
| `db_master` | `DbusBundle` | Native DBus peripheral interface. |
| `bram_a` | `RamPort32` | BRAM port A, instruction fetch (read-only). Driven directly from the instruction bus. |
| `bram_b` | `RamPort32` | BRAM port B, data access (read/write). Driven through the DBus interconnect when the CPU addresses the BRAM window. |
| `clock` | bit | Clock. |
| `reset` | bit | Synchronous active-high reset. |
| `config` | `BonfireConfig` | Core configuration (see [Core](core.md)). |
| `wb_mask` | `AdrMask` | Address mask for the Wishbone window. Default: top nibble `0x4` (0x40000000–0x4fffffff). |
| `db_mask` | `AdrMask` | Address mask for the native DBus peripheral window. Default: top nibble `0x8` (0x80000000–0x8fffffff). |
| `bram_mask` | `AdrMask` | Address mask for block RAM. Default: top nibble `0xc` (0xc0000000–0xcfffffff). |

### Internal structure

```
    CPU core (BonfireCoreTop)
         │ ibus ──────────────────────────── bram_a (instr. RAM port)
         │
         │ dbus
         ▼
    DbusInterConnects (1 master / 3 slaves)
         ├── bram_mask ──────────────────── bram_b (data RAM port)
         ├── wb_mask ────► DbusToWishbone ─► wb_master
         └── db_mask ────────────────────── db_master
```

`DbusToWishbone()` converts the native DBus to a Wishbone B4 master.

---

## `BonfireCoreSoC`

Defined in `rtl/soc/bonfire_core_soc.py`, `BonfireCoreSoC` is the full MyHDL
SoC that integrates `bonfireCoreExtendedInterface` with block RAM, a native LED
register, optional Wishbone exposure, and reset logic.

### Purpose

`BonfireCoreSoC` is the integration layer around the Bonfire RV32I CPU core. It
connects the core instruction and data buses to:

- dual-port block RAM used for code and data,
- a native DBus peripheral slot currently used by the LED register,
- a Wishbone master interface for external or wrapped peripherals.

The default reset address is `0xc0000000`, matching the block RAM address window.

### Top-level hardware method

```python
BonfireCoreSoC.bonfire_core_soc(
    sysclk,        # clock
    resetn,        # active-low external reset input
    uart0_tx,      # UART TX (loopback placeholder in the MyHDL SoC)
    uart0_rx,      # UART RX
    led,           # LED output vector
    o_resetn,      # reset output to board (driven high in normal mode)
    i_locked,      # PLL lock input
    wb_master=None,# optional Wishbone master (when exposeWishboneMaster=True)
    jtag_tck=None, # optional JTAG debug clock
    jtag_tms=None, # optional JTAG mode select
    jtag_tdi=None, # optional JTAG data in
    jtag_tdo=None, # optional JTAG data out
    jtag_trstn=None,# optional JTAG reset
)
```

It instantiates:

- `bonfireCoreExtendedInterface` — CPU core plus bus interconnect.
- `DualportedRamLaned` or `DualportedRam` — instruction/data memory.
- `led_out` — native DBus LED register.
- `wishbone_dummy` — dummy Wishbone target (when `exposeWishboneMaster=False`).
- `uart_dummy` — UART loopback placeholder.
- `reset_logic` or `no_reset_logic` — reset generation.
- `JtagDTM` — optional JTAG debug transport when `enableJtagDebug=True`.

### Address map

Address decoding uses bits `[31:28]` of the CPU data address.

| Region | Top nibble | Address range | Target |
| --- | ---: | --- | --- |
| Wishbone | `0x4` | `0x40000000` – `0x4fffffff` | Wishbone bridge |
| Native DBus | `0x8` | `0x80000000` – `0x8fffffff` | LED register |
| BRAM | `0xc` | `0xc0000000` – `0xcfffffff` | data RAM port |

The instruction bus is connected directly to the read-only RAM port. The data
bus reaches the RAM through the interconnect at the BRAM address window.

Addresses not matching one of these three windows return a DBus error.

### Memory

The SoC uses a dual-port RAM:

- port A: instruction fetch, read-only,
- port B: CPU data access, read/write.

The RAM is initialized from the `hexfile` passed to `BonfireCoreSoC`. The
default RAM address width is 11 words, i.e. `2**11` 32-bit words or 8 KiB.
FuseSoC targets can override this with `bram_adr_width`.

Two RAM implementations exist:

- `DualportedRamLaned`: four independent 8-bit lanes (default, recommended for
  byte-enable writes).
- `DualportedRam`: one 32-bit-wide memory.

### LED register

The LED register is the only native MyHDL MMIO peripheral.

It is mapped through the native DBus window at `0x80000000` and responds to any
address selected by the top-nibble decode. The implementation does not decode
lower address bits.

Behavior:

- writes update the LED register when `dbus.we_o[0]` is set,
- reads return the current LED register value in the low `numLeds` bits,
- `ack_i` follows `en_o`,
- `stall_i` is always false.

`numLeds` must be between 1 and 8. If `ledActiveLow` is true, the output pins
are inverted.

### Wishbone bridge

The CPU native DBus is converted to a Wishbone master by `DbusToWishbone()`.
The Wishbone address is word-addressed: DBus address bits `[31:2]` become the
Wishbone address.

When `exposeWishboneMaster=False`, the SoC instantiates `wishbone_dummy`:

- accepts every Wishbone cycle immediately,
- stores writes in a single 32-bit register,
- returns that register on reads,
- initializes to `0xdeadbeef`.

When `exposeWishboneMaster=True`, the Wishbone master bundle is exposed through
the generated top-level and no dummy is instantiated. This mode is used by the
[Extended SoC](extended-soc.md).

### UART status

The MyHDL SoC does not implement a real UART yet. `uart_dummy()` connects
`uart_tx = uart_rx` (loopback placeholder). Software cannot use the MyHDL UART
as a real serial peripheral.

For the extended SoC generation path, `gen_soc.py` wraps the MyHDL core with
`fusesoc-cores/templates/soc_top.vhd`, which exposes the Wishbone master to
external VHDL peripherals including a full UART implementation. See
[Extended SoC](extended-soc.md).

### Reset logic

The normal reset path is synchronous to `sysclk`:

- `resetn` is the active-low external reset input,
- `i_locked` is the PLL lock input,
- internal reset is asserted when `resetn` is low or `i_locked` is false,
- reset is passed through two flip-flops before reaching the logic.

`o_resetn` is currently driven high through a dummy signal in normal mode.

If `NoReset=True`, `no_reset_logic()` is used instead, driving internal reset
inactive and `o_resetn` high. This is mainly useful for special conversion or
test scenarios.

### Configuration

`BonfireCoreSoC` accepts a `soc_config` dictionary. Common keys are:

| Key | Default | Meaning |
| --- | --- | --- |
| `resetAdr` | `0xc0000000` | CPU reset address |
| `bramAdrWidth` | `11` | RAM depth as address width in 32-bit words |
| `NoReset` | `False` | Disable normal reset generation |
| `LanedMemory` | `True` | Use byte-laned RAM implementation |
| `numLeds` | `4` | LED output width |
| `ledActiveLow` | `True` | Invert LED output pins |
| `UseVHDLMemory` | `False` | Currently unused |
| `exposeWishboneMaster` | `False` | Expose Wishbone instead of using dummy |
| `enableJtagDebug` | `False` | Expose JTAG pins, instantiate `JtagDTM`, and connect it to the core debug module |

### FuseSoC generation

The SoC is generated through `fusesoc-cores/generators/gen_soc.py`.

Important FuseSoC parameters include:

| Parameter | `soc_config` key | Description |
| --- | --- | --- |
| `hexfile` | — | RAM initialization file |
| `bram_adr_width` | `bramAdrWidth` | RAM size |
| `laned_memory` | `LanedMemory` | Select lane-based RAM |
| `num_leds` | `numLeds` | LED vector width |
| `led_active_low` | `ledActiveLow` | LED polarity |
| `extended_soc` | — | Generate the VHDL wrapper (Extended SoC path) |
| `expose_wishbone_master` | `exposeWishboneMaster` | Expose Wishbone master directly |
| `enable_jtag_debug` | `enableJtagDebug` | Expose a JTAG DTM and forward it to the core debug module |

When `extended_soc` is true, `gen_soc.py` forces `exposeWishboneMaster=True` so
that `fusesoc-cores/templates/soc_top.vhd` can attach VHDL peripherals to the
Wishbone bus.

The plain `sim` target and the non-extended `icepizero` target enable
`enable_jtag_debug`, so the generated MyHDL SoC can exercise or expose the JTAG
debug path without requiring the Extended SoC wrapper.

### MyHDL testbench

The pure MyHDL testbench lives in `tb/soc/bonfire_core_soc_tb.py`. It can run
the SoC in two modes:

- internal Wishbone dummy — used by the LED firmware test,
- exposed Wishbone master connected to `Wishbone_bfm` — used by the Wishbone
  bridge firmware test.

Run with pytest:

```bash
pytest -vv tests/test_soc_myhdl.py
```

### Firmware smoke tests

Small SoC smoke-test programs are under `code/soc/apps`:

- `led`: writes an incrementing counter to the LED register.
- `wishbone`: writes and reads the Wishbone bridge, then reports success
  through the LED register.

Build examples:

```bash
make -C code soc SOC_APP=led SOC_PLATFORM=sim TARGET_PREFIX=riscv64-unknown-elf
make -C code soc SOC_APP=wishbone SOC_PLATFORM=sim TARGET_PREFIX=riscv64-unknown-elf
make -C code soc SOC_APP=led SOC_PLATFORM=icepizero TARGET_PREFIX=riscv64-unknown-elf
make -C code soc-all TARGET_PREFIX=riscv64-unknown-elf
```

### Current limitations

- UART is not implemented in the MyHDL SoC; only a loopback dummy exists.
- The LED register is the only native MyHDL peripheral.
- The LED register uses only the top-nibble DBus decode and ignores lower
  address bits.
- `UseVHDLMemory` is present but unused.
- Interrupt handling is not wired at the SoC level.
- On IcePi Zero, the new JTAG pins increase timing pressure around the debug
  `dpc` update path; this is tracked as a follow-up timing cleanup item.

---

## Source files

| File | Description |
| --- | --- |
| `rtl/soc/bonfire_core_soc.py` | `BonfireCoreSoC` — MyHDL SoC top-level generator |
| `rtl/uncore/bonfire_core_ex.py` | `bonfireCoreExtendedInterface` — CPU core + BRAM + native DBus + Wishbone |
| `rtl/uncore/dbus_interconnect.py` | `DbusInterConnects` — 1-master/3-slave DBus address decoder |
| `rtl/uncore/ram_dp.py` | `DualportedRamLaned`, `DualportedRam` — dual-port RAM implementations |
| `fusesoc-cores/templates/soc_top.vhd` | Generated VHDL wrapper around the MyHDL SoC |
| `fusesoc-cores/generators/gen_soc.py` | FuseSoC generator entry point for SoC VHDL conversion |

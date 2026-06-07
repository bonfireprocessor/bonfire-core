# Interfaces and Memory

This page describes the non-core hardware support blocks: the internal bus
protocol, the Wishbone bridge, the DBus interconnect, and the dual-port RAM
helpers.

---

## DBus (`DbusBundle`)

Defined in `rtl/bonfire_interfaces.py`.

`DbusBundle` is the internal bus used between the CPU core and every memory or
peripheral. It is a simple pipelined bus loosely based on the Wishbone B4
pipelined mode. Signal names follow master convention.

### Signals

| Signal | Direction | Width | Description |
| --- | --- | --- | --- |
| `en_o` | master → slave | 1 | Transaction enable / valid. |
| `adr_o` | master → slave | XLEN | Byte address. The lowest `log2(XLEN/8)` bits are always zero. |
| `we_o` | master → slave | XLEN/8 | Byte-wide write-enable strobes. Zero for reads. |
| `db_wr` | master → slave | XLEN | Write data. |
| `stall_i` | slave → master | 1 | Stall: the slave cannot accept a new transaction yet. A slave that does not support pipelining keeps `stall_i` high until `ack_i` is asserted. |
| `ack_i` | slave → master | 1 | Acknowledge: data written or read data available on `db_rd`. Terminates the cycle. |
| `error_i` | slave → master | 1 | Bus error: raised instead of `ack_i` when the access cannot be completed. |
| `db_rd` | slave → master | XLEN | Read data. Valid when `ack_i` is asserted. |

Read-only `DbusBundle` instances (instruction bus) omit `we_o` and `db_wr`.

### Address conventions

- `adrLow` = `log2(XLEN/8)` = 2 for 32-bit — the lowest two address bits are
  always zero (word-aligned).
- The DBus address is a full byte address. The Wishbone bridge strips the low
  bits.

---

## Wishbone master (`Wishbone_master_bundle`)

Defined in `rtl/bonfire_interfaces.py`.

`Wishbone_master_bundle` wraps a Wishbone B4 master interface. It is
configurable with the following constructor parameters:

| Parameter | Default | Description |
| --- | --- | --- |
| `adrHigh` | `32` | Highest address bit (exclusive Python range). |
| `adrLow` | `2` | Lowest address bit (word-aligned). |
| `dataWidth` | `32` | Data bus width in bits. |
| `granularity` | `8` | Port granularity in bits; controls `wbm_sel_o` width. |
| `b4_pipelined` | `False` | Generate `wbm_stall_i` for Wishbone B4 pipelined mode. |
| `bte_signals` | `False` | Generate `wbm_cti_o` and `wbm_bte_o` for burst support. |
| `createErrorSignal` | `False` | Generate `wbm_err_i`. |

### Signals

| Signal | Direction | Description |
| --- | --- | --- |
| `wbm_cyc_o` | master → slave | Bus cycle active. |
| `wbm_stb_o` | master → slave | Strobe: data valid on the address/data lines. |
| `wbm_we_o` | master → slave | Write enable. |
| `wbm_adr_o` | master → slave | Word address (`[adrHigh:adrLow]` from DBus byte address). |
| `wbm_db_o` | master → slave | Write data. |
| `wbm_sel_o` | master → slave | Byte select. |
| `wbm_ack_i` | slave → master | Acknowledge. |
| `wbm_db_i` | slave → master | Read data. |
| `wbm_err_i` | slave → master | Error (optional, when `createErrorSignal=True`). |
| `wbm_stall_i` | slave → master | Stall (optional, when `b4_pipelined=True`). |
| `wbm_cti_o` | master → slave | Cycle type indicator (optional, when `bte_signals=True`). |
| `wbm_bte_o` | master → slave | Burst type extension (optional, when `bte_signals=True`). |

---

## DBus-to-Wishbone bridge (`DbusToWishbone`)

Defined in `rtl/bonfire_interfaces.py`.

`DbusToWishbone()` is a MyHDL block that converts a `DbusBundle` to a
`Wishbone_master_bundle`. It adapts automatically to the Wishbone configuration:

- Standard (non-pipelined): converts by keeping `cyc_o` active until `ack_i`
  arrives, so a standard Wishbone slave sees one request at a time.
- Pipelined: passes `stall_i` back to the DBus `stall_i`.

The Wishbone address is the DBus address bits `[adrHigh:adrLow]`, i.e. the byte
address stripped of the lowest alignment bits.

---

## DBus interconnect (`DbusInterConnects`)

Defined in `rtl/uncore/dbus_interconnect.py`.

`DbusInterConnects.Master3Slaves()` is a simple 1-master / 3-slave address
decoder for the DBus. It routes CPU data bus transactions to one of three
slaves based on address masking.

### `AdrMask`

`AdrMask(width, bit, value)` matches when bits `[bit+log2(value):bit]` of the
address equal `value`. In the default SoC configuration:

| `AdrMask` | Matched top nibble | Address range |
| --- | --- | --- |
| `AdrMask(32, 28, 0x4)` | `0x4` | `0x40000000` – `0x4fffffff` |
| `AdrMask(32, 28, 0x8)` | `0x8` | `0x80000000` – `0x8fffffff` |
| `AdrMask(32, 28, 0xc)` | `0xc` | `0xc0000000` – `0xcfffffff` |

When no mask matches, the interconnect returns a DBus error.

---

## Dual-port RAM (`ram_dp`)

Defined in `rtl/uncore/ram_dp.py`.

The SoC uses a dual-port RAM for both instruction and data access.

### `DualportedRamLaned` (default)

Four independent 8-bit lanes. This is the recommended implementation because
it directly supports byte-enable writes, which are required by the RISC-V
`SB` / `SH` store instructions.

### `DualportedRam`

One 32-bit-wide memory. Does not support byte granularity directly.

### `RamPort32`

`RamPort32` is the bundle used to connect a bus to a RAM port:

| Signal | Direction | Description |
| --- | --- | --- |
| `adr` | in | Word address. |
| `dat_rd` | out | Read data. |
| `dat_wr` | in | Write data. |
| `we` | in | Byte-wide write enable (4 bits for 32-bit data). |
| `en` | in | Port enable. |

`dbusToRamPort()` connects a `DbusBundle` to a `RamPort32`, handling address
alignment and byte-enable mapping.

---

## Source files

| File | Description |
| --- | --- |
| `rtl/bonfire_interfaces.py` | `DbusBundle`, `Wishbone_master_bundle`, `DbusToWishbone`, `ControlBundle`, `DebugOutputBundle` |
| `rtl/uncore/dbus_interconnect.py` | `DbusInterConnects`, `AdrMask` |
| `rtl/uncore/ram_dp.py` | `DualportedRamLaned`, `DualportedRam`, `RamPort32`, `dbusToRamPort` |

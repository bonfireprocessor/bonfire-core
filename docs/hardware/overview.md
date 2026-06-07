# Hardware Overview

This section groups the hardware-oriented documentation for the Bonfire core
and its SoC-level integration.

## Architecture hierarchy

```
┌──────────────────────────────────────────────────────────┐
│  Extended SoC VHDL top-level (bonfire_core_soc_top)       │
│  fusesoc-cores/templates/soc_top.vhd                      │
│                                                           │
│  ┌────────────────────────────────────────────────────┐   │
│  │  BonfireCoreSoC  (rtl/soc/bonfire_core_soc.py)     │   │
│  │                                                    │   │
│  │  ┌─────────────────────────────────────────────┐  │   │
│  │  │  bonfireCoreExtendedInterface               │  │   │
│  │  │  (rtl/uncore/bonfire_core_ex.py)            │  │   │
│  │  │                                             │  │   │
│  │  │  ┌─────────────────────────────────────┐   │  │   │
│  │  │  │  BonfireCoreTop                     │   │  │   │
│  │  │  │  (rtl/bonfire_core_top.py)          │   │  │   │
│  │  │  │                                     │   │  │   │
│  │  │  │  FetchUnit ──► Decode ──► Execute   │   │  │   │
│  │  │  └─────────────────────────────────────┘   │  │   │
│  │  │                                             │  │   │
│  │  │  DualportedRamLaned (BRAM A+B)              │  │   │
│  │  │  DbusInterConnects                          │  │   │
│  │  │  DbusToWishbone                             │  │   │
│  │  └─────────────────────────────────────────────┘  │   │
│  │                                                    │   │
│  │  LED register (native DBus)                        │   │
│  │  Reset logic                                       │   │
│  └────────────────────────────────────────────────────┘   │
│                                                           │
│  VHDL Wishbone peripherals (bonfire_soc_io)               │
│    UART0 / UART1 / SPI / GPIO                             │
└──────────────────────────────────────────────────────────┘
```

## Scope

The repository contains:

- `BonfireCoreTop` — the configurable RV32I processor core (3-stage pipeline).
- `bonfireCoreExtendedInterface` — connects the CPU to BRAM, native DBus, and
  Wishbone via an address-decoded interconnect.
- `BonfireCoreSoC` — the MyHDL SoC integrating the above with RAM, LED register,
  reset logic, and optional Wishbone exposure.
- Extended SoC generation — a FuseSoC generator that converts the MyHDL SoC to
  VHDL and wraps it with a full VHDL peripheral block.

## Documentation pages

- **[Core](core.md)** — pipeline architecture, `BonfireCoreTop`, `BonfireConfig`.
- **[SoC](soc.md)** — `bonfireCoreExtendedInterface` and `BonfireCoreSoC`,
  address map, peripherals, FuseSoC generation.
- **[Extended SoC](extended-soc.md)** — generated VHDL wrapper, peripheral
  selection, FuseSoC targets, FPGA builds.
- **[Interfaces and Memory](interfaces-and-memory.md)** — `DbusBundle`,
  Wishbone master, DBus interconnect, dual-port RAM.

## Main implementation areas

- `rtl/` — hardware-describing MyHDL code
- `rtl/uncore/` — interconnect and RAM helper blocks
- `rtl/soc/` — SoC integration code
- `tb/` — MyHDL testbench code
- `fusesoc-cores/` — FuseSoC generator and template infrastructure

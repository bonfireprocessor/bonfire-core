# SoC

The repository currently contains documentation for both the MyHDL SoC wrapper and the Extended SoC flow.

## Bonfire Core SoC

The MyHDL `BonfireCoreSoC` wrapper integrates the core with:

- dual-port block RAM,
- a native DBus peripheral slot,
- a Wishbone master interface,
- reset handling,
- small board-/simulation-facing top-level signals.

The default reset address currently matches the block RAM window at `0xc0000000`.

## Extended SoC

The Extended SoC documentation covers the larger simulation and generation flow around the SoC, including UART/GPIO-oriented smoke testing and FuseSoC-based generation.

## Related source files

- `soc/SOC.md`
- `soc/EXTENDED_SOC.md`
- `rtl/soc/bonfire_core_soc.py`
- `rtl/uncore/bonfire_core_ex.py`
- `fusesoc-cores/`

## Planned expansion

A later version of this page should likely be split into:

- SoC architecture,
- address map and peripherals,
- simulation flow,
- generated VHDL flow.

# Interfaces and Memory

This page groups the non-core hardware support blocks that are already documented or visible in the RTL layout.

## Current topics

- DBus bundles and interconnect
- Wishbone master bridge
- dual-port RAM helpers
- SoC-local LED and simple peripheral integration

## Main implementation files

- `rtl/bonfire_interfaces.py`
- `rtl/uncore/dbus_interconnect.py`
- `rtl/uncore/ram_dp.py`
- `rtl/uncore/bonfire_core_ex.py`

## Related source files

- `soc/SOC.md`
- `soc/EXTENDED_SOC.md`

## Planned expansion

This page should later describe:

- bus roles and responsibilities,
- address decoding,
- RAM organization,
- Wishbone exposure and integration points.

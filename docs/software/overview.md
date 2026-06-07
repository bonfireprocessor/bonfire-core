# Software Overview

This section covers the software artifacts that ship with the repository and
support hardware bring-up, simulation, and verification.

## Scope

The repository includes:

- core-oriented RISC-V assembly test programs (`code/core-tests/`),
- SoC-oriented C firmware examples (`code/soc/apps/`),
- a minimal SoC runtime library (`code/soc/runtime/`),
- build outputs under `code/build/`,
- RISC-V compliance test integration.

## Pages

- **[Core Test Programs](core-test-programs.md)** — assembly test programs used
  by the core integration tests; how to build and run them.
- **[SoC Applications](soc-applications.md)** — C firmware for the MyHDL SoC
  and Extended SoC simulations; LED, Wishbone, hello, and monitor applications.
- **[Build Artifacts](build-artifacts.md)** — summary of generated `.hex`,
  `.elf`, `.lst`, and `.sym` files and where to find them.
- **[Compliance](compliance.md)** — how to run the RISC-V compliance suite
  against Bonfire Core.

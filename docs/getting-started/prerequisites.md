# Prerequisites

## Python environment

Bonfire Core currently expects:

- Python
- `pip`
- a local virtual environment in `.venv/` (recommended)

The project README notes successful use with Python versions in the range **3.8 .. 3.13.5**.

## Python packages

The main Python-side dependencies mentioned in the existing documentation are:

- `myhdl==0.11.51`
- `pytest`
- `pyelftools`

## RISC-V toolchain

A RISC-V non-Linux ELF toolchain is required for building the test programs and SoC firmware.

Typical commands referenced in the current documentation use the `riscv64-unknown-elf-*` toolchain family.

Example Debian packages mentioned in `README.md`:

```bash
sudo apt install \
  binutils-riscv64-unknown-elf \
  gcc-riscv64-unknown-elf \
  picolibc-riscv64-unknown-elf \
  libstdc++-riscv64-unknown-elf-picolibc
```

## Related source file

- `README.md`

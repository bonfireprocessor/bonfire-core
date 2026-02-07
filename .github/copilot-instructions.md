# bonfire-core AI Agent Instructions

## Project Overview

**bonfire-core** is a configurable RISC-V RV32I core written in **MyHDL** (Python-based HDL). The design uses a **3-stage pipeline** (fetch → decode → execute) and targets both simulation and FPGA synthesis via VHDL conversion through FuseSoC.

## Architecture

### Pipeline Structure
- **Fetch** ([rtl/fetch.py](../rtl/fetch.py)): Instruction fetch unit, interfaces with instruction bus
- **Decode** ([rtl/decode.py](../rtl/decode.py)): Instruction decoder, extracts operands and control signals
- **Execute** ([rtl/execute.py](../rtl/execute.py)): Contains ALU, load/store unit, trap/CSR logic

### Key Components
- **Top-level**: [rtl/bonfire_core_top.py](../rtl/bonfire_core_top.py) — instantiates fetch + backend
- **Backend**: [rtl/simple_pipeline.py](../rtl/simple_pipeline.py) — coordinates decode/execute/regfile
- **ALU**: [rtl/alu.py](../rtl/alu.py) — arithmetic/logic operations with barrel shifter
- **Load/Store**: [rtl/loadstore.py](../rtl/loadstore.py) — memory access with pipelined support
- **CSR/Trap**: [rtl/trap.py](../rtl/trap.py), [rtl/csr.py](../rtl/csr.py) — privilege/exception handling

### MyHDL Design Patterns

1. **Bundle Classes**: Interface definitions (e.g., `DbusBundle`, `FetchInputBundle`, `ExecuteBundle`)
   - Located in [rtl/bonfire_interfaces.py](../rtl/bonfire_interfaces.py) and module files
   - Contain `Signal` declarations for inter-module communication
   - Example: `DbusBundle` provides Wishbone-like bus interface

2. **@block Decorator**: Hardware generators — functions decorated with `@block` return synthesizable instances
   ```python
   @block
   def SimpleFetchUnit(self, fetchBundle, ibus, clock, reset):
       # hardware description
       return instances()
   ```

3. **Configuration**: [rtl/config.py](../rtl/config.py) — `BonfireConfig` class controls:
   - Shifter mode (pipelined vs combinatorial)
   - Load/Store outstanding requests
   - Jump bypass optimization
   - Reset address

## Development Workflow

### Primary Entry Point
**Use `scripts/bonfire-core`** — universal test runner that manages venv, toolchain, and pytest

```bash
# Setup: create venv + install dependencies
scripts/bonfire-core --install

# Run all tests (unit + integration)
scripts/bonfire-core --all

# Unit tests only
scripts/bonfire-core --ut

# Run single HEX program with VCD trace
scripts/bonfire-core --hex code/build/loadsave.hex --vcd /tmp/debug.vcd
```

### Test Structure (pytest-based)
All tests live in [tests/](../tests/) directory:
- **Unit tests**: `test_ut_*.py` (ALU, shifter, decoder, regfile, loadstore)
- **Pipeline integration**: `test_integration_pipeline.py`
- **Core integration**: `test_core.py` (runs [code/](../code/) test programs)
- **Compliance adapter**: `test_compliance_single.py` (called by riscv-compliance harness)

### Test Programs
Small RISC-V assembly programs in [code/](../code/):
- Built with `make all TARGET_PREFIX=riscv64-unknown-elf`
- Generate `.elf` (symbols) and `.hex` (32-bit word hexdump for testbench)
- Use **monitor convention**: write `1` to `0x10000000` for success, `-1` for failure
- See [code/README.md](../code/README.md) for program descriptions

### Legacy Runner
[tb_run.py](../tb_run.py) still available for debugging but **not recommended** for daily use. See [TB_RUN.md](../TB_RUN.md).

## RISC-V Compliance Testing

Uses the [bonfireprocessor/riscv-compliance](https://github.com/bonfireprocessor/riscv-compliance) fork.

```bash
# From riscv-compliance repo:
./scripts/run_bonfire_compliance.sh RISCV_TARGET=bonfire-core
```

Compliance harness calls [tests/test_compliance_single.py](../tests/test_compliance_single.py), which:
- Reads `BONFIRE_COMPLIANCE_ELF`, `BONFIRE_COMPLIANCE_HEX`, `BONFIRE_COMPLIANCE_SIG` env vars
- Runs [tb/tb_core.py](../tb/tb_core.py) testbench
- Dumps memory signature via [tb/sim_monitor.py](../tb/sim_monitor.py)

See [COMPLIANCE.md](../COMPLIANCE.md) for details.

## Toolchain Requirements

- **Python 3.8–3.13** with venv
- **MyHDL 0.11.51** (exact version for FuseSoC compatibility)
- **pytest**, **pyelftools**
- **RISC-V toolchain**: `riscv64-unknown-elf-*` with RV32I multilib support
  ```bash
  # Debian/Ubuntu example:
  sudo apt install binutils-riscv64-unknown-elf gcc-riscv64-unknown-elf
  ```

## FuseSoC Integration

bonfire-core uses **FuseSoC generators** to convert MyHDL → VHDL for simulation/synthesis:
- Core definition: [bonfire-core.core](../bonfire-core.core)
- SoC definition: [bonfire-core-soc.core](../bonfire-core-soc.core)
- Generators: [gen_core.py](../gen_core.py), [gen_soc.py](../gen_soc.py)

Generate VHDL and simulate:
```bash
fusesoc run --target=sim bonfire-core --testfile=code/build/loop.hex
```

## Key Conventions

### File Organization
- **rtl/**: Core MyHDL modules (fetch, decode, execute, etc.)
- **tb/**: Testbenches (unit + integration)
- **tests/**: pytest test suite
- **code/**: Assembly test programs
- **uncore/**: Peripherals (RAM, interconnect, monitor)
- **soc/**: SoC wrapper
- **vhdl/**: Hand-written VHDL testbench components
- **vhdl_gen/**: MyHDL-generated VHDL (created by FuseSoC)

### Naming Patterns
- **Bundle suffix**: Interface/signal groups (e.g., `FetchInputBundle`, `ExecuteBundle`)
- **tb_ prefix**: Testbench modules (e.g., `tb_core.py`, `tb_alu.py`)
- **test_ prefix**: pytest test files (e.g., `test_ut_alu.py`)

### Signal Conventions
- `_i` suffix: input signal
- `_o` suffix: output signal
- `en_`, `valid_`: enable/valid flags
- `stall_`, `ack_`: control flow signals

## Debugging

### VCD Traces
Generate waveforms for debug:
```bash
scripts/bonfire-core --hex code/build/loadsave.hex --vcd ~/debug.vcd
# Opens as ~/debug.vcd.vcd (MyHDL appends .vcd)
```

### Monitor Output
Run pytest with `-s` to see testbench prints:
```bash
pytest -s tests/test_core.py -k loadsave
```

Monitor writes appear as:
```
Monitor write: @570 10000200: fa55aa55 (-95049131)
```

## CI/CD

GitHub Actions workflows in [.github/workflows/](../../../.github/workflows/):
- **unit-tests.yml**: Runs on every push, executes pytest suite
- **riscv-compliance.yml**: Nightly + manual, runs full compliance suite (rv32i + rv32Zicsr)

## Common Pitfalls

1. **MyHDL version matters**: Must use 0.11.51 for FuseSoC; newer versions break conversion
2. **Signal vs intbv vs modbv**: Use `Signal(intbv(...))` for registers, `modbv` for PC/addresses that wrap
3. **@always_comb vs @always**: Combinatorial logic must use `@always_comb` or `@always(...)` with sensitivity list
4. **RISC-V toolchain prefix**: Code Makefile expects `riscv32-unknown-elf-*`, but `riscv64-unknown-elf-*` works with multilib
5. **Testbench RAM size**: Default 16KB at address 0; test programs must fit within this constraint

## Quick Reference

| Task | Command |
|------|---------|
| Setup environment | `scripts/bonfire-core --install` |
| Run all tests | `scripts/bonfire-core` or `scripts/bonfire-core --all` |
| Unit tests only | `scripts/bonfire-core --ut` |
| Integration tests | `scripts/bonfire-core --integration` |
| Build test code | `make -C code all TARGET_PREFIX=riscv64-unknown-elf` |
| Debug single program | `scripts/bonfire-core --hex code/build/loop.hex --vcd /tmp/trace.vcd` |
| Run compliance | `cd riscv-compliance && ./scripts/run_bonfire_compliance.sh` |
| Generate VHDL | `fusesoc run --target=sim bonfire-core --testfile=code/build/loop.hex` |

## Further Reading

- [README.md](../README.md) — Project overview, setup, test workflow
- [TB_RUN.md](../TB_RUN.md) — Legacy tb_run.py documentation
- [COMPLIANCE.md](../COMPLIANCE.md) — RISC-V compliance testing
- [scripts/README.md](../scripts/README.md) — Universal runner documentation
- [tests/README.md](../tests/README.md) — Pytest test suite structure
- [code/README.md](../code/README.md) — Test program descriptions

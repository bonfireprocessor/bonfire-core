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
- **Divider**: [rtl/divider.py](../rtl/divider.py) — Non-Restoring Division (NRD) unit (not yet integrated into pipeline)
- **Load/Store**: [rtl/loadstore.py](../rtl/loadstore.py) — memory access with pipelined support
- **CSR/Trap**: [rtl/trap.py](../rtl/trap.py), [rtl/csr.py](../rtl/csr.py) — privilege/exception handling

### MyHDL Design Patterns

1. **Bundle Classes**: Interface definitions (e.g., `DbusBundle`, `FetchInputBundle`, `ExecuteBundle`, `DividerBundle`)
   - Located in [rtl/bonfire_interfaces.py](../rtl/bonfire_interfaces.py) and module files
   - Contain `Signal` declarations for inter-module communication
   - Bundle classes can have `@block` methods that operate on their own signals
   - Example: `DbusBundle` provides Wishbone-like bus interface
   - Example: `DividerBundle` in [rtl/divider.py](../rtl/divider.py) has `Complementor()` and `divider()` methods
   ```python
   class DividerBundle:
       def __init__(self):
           self.op1_i = Signal(modbv(0)[32:])
           self.op2_i = Signal(modbv(0)[32:])
           # ... more signals
       
       @block
       def divider(self, clock, reset):
           # hardware description using self.op1_i, self.op2_i, etc.
           return instances()
   ```

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
- **Unit tests**: `test_ut_*.py` (ALU, shifter, decoder, regfile, loadstore, divider)
  - Self-checking testbenches with stimulus + expected results
  - Use DUT's Bundle classes directly for clean interfaces
  - Enable VCD tracing to `waveforms/` directory for debugging
  - Example: [tests/test_ut_divider.py](../tests/test_ut_divider.py) tests 44 division cases
- **Conversion tests**: `test_*_convert.py`
  - Verify VHDL conversion capability
  - Use wrapper block pattern to eliminate warnings
  - Output to `vhdl_gen/` directory
  - Example: [tests/test_divider_convert.py](../tests/test_divider_convert.py)
- **Pipeline integration**: `test_integration_pipeline.py`
- **Core integration**: `test_core.py` (runs [code/](../code/) test programs)

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

Compliance harness calls [run_compliance.sh](../run_compliance.sh), which:
- Activates bonfire-core venv
- Runs [run_compliance.py](../run_compliance.py) with `--hex`, `--elf`, `--sig` arguments
- Executes [tb/tb_core.py](../tb/tb_core.py) testbench directly (no pytest overhead)
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
- **rtl/**: Core MyHDL modules (fetch, decode, execute, divider, etc.)
- **tb/**: Testbenches (unit + integration)
- **tests/**: pytest test suite
  - `test_ut_*.py`: Unit tests for individual modules
  - `test_*_convert.py`: VHDL conversion verification tests
  - `test_integration_*.py`: Pipeline integration tests
  - `test_core.py`: Full core integration tests
- **code/**: Assembly test programs
- **uncore/**: Peripherals (RAM, interconnect, monitor)
- **soc/**: SoC wrapper
- **vhdl/**: Hand-written VHDL testbench components
- **vhdl_gen/**: MyHDL-generated VHDL (created by FuseSoC or conversion tests)
- **waveforms/**: VCD trace files from test runs (project-local, not committed)

### Naming Patterns
- **Bundle suffix**: Interface/signal groups (e.g., `FetchInputBundle`, `ExecuteBundle`)
- **tb_ prefix**: Testbench modules (e.g., `tb_core.py`, `tb_alu.py`)
- **test_ prefix**: pytest test files (e.g., `test_ut_alu.py`)

### Signal Conventions
- `_i` suffix: input signal
- `_o` suffix: output signal
- `en_`, `valid_`: enable/valid flags
- `stall_`, `ack_`: control flow signals

## VHDL Conversion Guidelines

When writing MyHDL code for VHDL conversion:

1. **Use intbv with explicit ranges for counters/indices**:
   ```python
   cnt = Signal(intbv(0, min=0, max=35))  # ✓ Works
   cnt = Signal(modbv(0, min=0, max=35))  # ✗ Converter fails
   ```

2. **Simplify boolean operations**:
   ```python
   # ✗ Converter dislikes mixed bool operations
   result = (bool(a) ^ bool(b)) and bool(c)
   
   # ✓ Separate XOR from AND
   xor_result = bool(a ^ b)
   result = xor_result and not c
   ```

3. **Use wrapper block pattern to eliminate conversion warnings**:
   ```python
   @block
   def DividerWrapper(bundle, clock, reset):
       # Create internal signals
       internal_sig = Signal(modbv(0)[32:])
       
       # Instantiate actual divider
       divider_inst = bundle.divider(clock, reset)
       
       # Wire signals in @always_comb
       @always_comb
       def connect():
           internal_sig.next = bundle.result_o
       
       return instances()
   ```

4. **Test conversion separately**: Create `test_*_convert.py` files
   ```python
   def test_divider_vhdl_conversion():
       bundle = DividerBundle()
       wrapper = DividerWrapper(bundle, clock, reset)
       wrapper.convert(hdl='VHDL', path='vhdl_gen', name='divider')
       # Check for warnings in conversion output
   ```

5. **Common conversion errors**:
   - "Cannot determine size of variable" → Add explicit `intbv(0, min=0, max=N)`
   - "Cannot infer" → Simplify expressions, avoid mixed types
   - "Not supported" → Check if using Python features not in VHDL (e.g., `//` operator)

## Debugging

### VCD Traces
Generate waveforms for debug:
```bash
scripts/bonfire-core --hex code/build/loadsave.hex --vcd ~/debug.vcd
# Opens as ~/debug.vcd.vcd (MyHDL appends .vcd)
```

Pytest tests with VCD tracing (see [tests/conftest.py](../tests/conftest.py)):
```python
@pytest.fixture
def waveforms_dir():
    repo_root = Path(__file__).parent.parent
    waveform_dir = repo_root / "waveforms"
    waveform_dir.mkdir(exist_ok=True)
    return waveform_dir

# Use in tests:
def test_divider_unsigned(waveforms_dir):
    vcd_file = waveforms_dir / "divider_unsigned.vcd"
    # ... testbench with tracing
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
- **unit-tests.yml**: Runs on every push to all branches
  - Runs all tests in tests/ directory
  - Automatically includes new tests without workflow updates
  - Runs ~28 tests including unit, integration, and conversion tests
- **riscv-compliance.yml**: Runs on push, PRs, nightly (2 AM UTC), and manual trigger
  - Full compliance suite (rv32i + rv32Zicsr)
  - Can run on feature branches for testing
  - Duration: ~2 minutes (fast) to 90 minutes (full suite)

## Git Workflow Best Practices

### Feature Branch Development
- Work on feature branches (e.g., `bot`) separate from `master`
- Test thoroughly before merging to default branch
- Use descriptive branch names

### Commit Management
- **Always backup before complex git operations**:
  ```bash
  mkdir -p temp/backup_myfeature/
  cp rtl/mymodule.py temp/backup_myfeature/
  ```
- **Squashing commits**: Use `git reset --soft` for safety
  ```bash
  # Example: squash last 3 commits
  git reset --soft HEAD~3
  git commit -m "Comprehensive commit message"
  ```
- Avoid interactive rebase if unfamiliar with editor handling
- Write comprehensive commit messages for squashed commits

### Pushing Changes
- Push feature branches for CI/CD testing before merging
- Check GitHub Actions tab for workflow results
- Both unit-tests and compliance workflows trigger on all branches (with `push:` trigger)

## Common Pitfalls

1. **MyHDL version matters**: Must use 0.11.51 for FuseSoC; newer versions break conversion
2. **Signal vs intbv vs modbv**:
   - Use `Signal(intbv(...))` for registers
   - Use `modbv` for values that need auto-wrapping (like VHDL wrapping behavior)
   - For VHDL conversion: use `intbv(0, min=0, max=N)` with explicit min/max
   - **NEVER** use `modbv(0, min=0, max=N)` - VHDL converter will fail!
3. **@always_comb vs @always**: Combinatorial logic must use `@always_comb` or `@always(...)` with sensitivity list
4. **@always_comb with Python constants**: Don't use `@always_comb` to compute constants from other constants
   - Empty sensitivity list causes issues
   - Set constants directly in stimulus instance instead
5. **RISC-V toolchain prefix**: Code Makefile expects `riscv32-unknown-elf-*`, but `riscv64-unknown-elf-*` works with multilib
6. **Testbench RAM size**: Default 16KB at address 0; test programs must fit within this constraint
7. **VHDL Converter is stricter than simulator**: Always test VHDL conversion separately
   - Create `test_*_convert.py` files for conversion verification
   - Simulator may accept code that converter rejects

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

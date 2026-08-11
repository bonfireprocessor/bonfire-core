# Tests (pytest)

This directory contains pytest-based tests for bonfire-core.

Tests are organized by execution level and scope, replacing the historical tb_run.py workflow with a modern test infrastructure:

- `pure/` — pure MyHDL/Python tests without HEX/ELF program loading
- `system/` — larger integration tests that load firmware images or exercise a fuller system path
- `conversion/` — VHDL conversion checks grouped by domain
- `fusesoc/` — FuseSoC packaging/build integration tests

## Run everything

```bash
cd bonfire-core
. .venv/bin/activate
pytest
```

## Test layout

### Pure MyHDL tests (`pure/`)

These are unit tests for individual modules (ALU, shifter, decoder, etc.) and use self-checking testbenches with built-in assertions or VCD traces for visual inspection of results.

**Files:**
- `tests/pure/core/test_alu.py` — ALU operations including all arithmetic/logic instructions
- `tests/pure/core/test_barrel_shifter.py` — Barrel shifter unit (comb, pipelined variants)
- `tests/pure/core/test_decoder.py` — Instruction decoder for RISC-V base ISA
- `tests/pure/core/test_regfile.py` — Register file operations and write-back logic
- `tests/pure/core/test_loadstore.py` — Load/Store unit with outstanding request support
- `tests/pure/core/test_pipeline.py` — Pipeline integration tests (fetch, backend)

### System core tests (`system/core`)

These integration tests run actual RISC-V firmware images (.hex or .elf) through the bonfire-core processor and check monitor output for expected results. The monitor follows the convention: write `1` at address `0x10000000` on success, `-1` on failure.

**Files:**
- `tests/system/core/test_core_programs.py` — Tests all buildable HEX programs from `code/build/core-tests/`

Run:
```bash
pytest -vv tests/system/core/test_core_programs.py
# tb_run-style monitor output with pytest's -s flag
pytest -s -vv tests/system/core/test_core_programs.py
```

Run a single program (examples):
```bash
pytest -s -vv tests/system/core/test_core_programs.py --bonfire-hex code/build/core-tests/loadsave.hex
```

### System SoC tests (`system/soc`)

Purpose: Run the pure MyHDL SoC testbench with pytest.

Pytest file:
- `tests/system/soc/test_soc_tb.py`

The test runs two variants:

- `code/build/soc/sim/led.hex` with the internal Wishbone dummy.
- `code/build/soc/sim/wishbone.hex` with the Wishbone master exposed and connected to `Wishbone_bfm`.

The firmware image can be overridden with `--bonfire-hex`.

### Debug system tests (`system/debug`)

Tests for debug modules, GDB server protocol, OpenOCD remote bitbang interface.

**Files:**
- `tests/system/debug/test_debug_module.py` — Debug module operations
- `tests/system/debug/test_gdbserver_protocol.py` — GDBstub protocol implementation
- `tests/system/debug/test_openocd_remote_bitbang.py` — OpenOCD integration

### VHDL Conversion tests (`conversion/`)

These tests verify that MyHDL code converts cleanly to synthesizable VHDL. Each conversion test creates temporary VHDL files and checks for warnings or errors.

**Files:**
- `tests/conversion/core/test_vhdl_conversion_core.py` — Core RTL components
- `tests/conversion/debug/test_vhdl_conversion_debug.py` — Debug module RTL
- `tests/conversion/soc/test_vhdl_conversion_soc.py` — SoC wrapper RTL
- `tests/conversion/uncore/test_uart_vhdl_conversion.py` — UART controller RTL

### FuseSoC integration tests (`fusesoc/`)

Tests for FuseSoC package generation, VHDL output, and simulation through fusesoc.

**File:**
- `tests/fusesoc/test_core.py` — FuseSoC core generation and simulation

---

## Running Individual Test Types

### Unit Tests Only

Run self-checking unit tests for individual modules:

```bash
pytest -vv tests/pure/
```

### Integration Tests Only

Run full system tests with firmware images:

```bash
pytest -s -vv tests/system/core/test_core_programs.py
pytest -vv tests/system/soc/test_soc_tb.py
```

### Single HEX Program Test

Run a specific core integration test program:

```bash
pytest -k "loadsave" -s -vv --bonfire-hex=code/build/core-tests/loadsave.hex
```

### VHDL Conversion Tests

Verify MyHDL → VHDL conversion for components:

```bash
pytest -vv tests/conversion/
```

### With Waveform Tracing (VCD)

Enable VCD tracing for debugging by selecting specific test with waveform output:

```bash
pytest --waveform --vcd=my_trace core_test_name --bonfire-hex=test.hex
```

Useful for visual inspection of timing, pipeline hazards, etc. in tools like GTKWave.

---

## Build Requirements

Tests require:

- Python 3.8–3.13 with venv
- MyHDL 0.11.51 (exact version)
- pytest + pyelftools
- RISC-V toolchain: `riscv64-unknown-elf-*` or `riscv32-unknown-elf-*`

Setup:

```bash
scripts/bonfire-core --install  # Creates venv and installs dependencies
make -C code all TARGET_PREFIX=riscv64-unknown-elf
pytest
```

# Tests (pytest + legacy mapping)

This directory contains the pytest-based test suite for bonfire-core.

It covers the same *test intents* that historically existed in the `tb_run.py` workflow:

- **Module unit tests** (ALU, shifter, decoder, regfile)
- **Load/Store unit tests** (LSU behavior/configurations)
- **Pipeline integration tests** (backend + fetch)
- **Core integration tests** (run full core against small programs)
- **SoC integration tests** (run the pure MyHDL SoC testbench)

For the legacy `tb_run.py` commands, see: [`../TB_RUN.md`](../TB_RUN.md)

## Run everything

```bash
cd bonfire-core
. .venv/bin/activate
pytest
```

## Test groups

### Module unit tests
Purpose: validate individual modules in isolation.

Pytest files:
- `test_ut_alu.py`
- `test_ut_barrel_shifter.py`
- `test_ut_decoder.py`
- `test_ut_regfile.py`

Run:
```bash
pytest -vv tests/test_ut_alu.py
pytest -vv tests/test_ut_barrel_shifter.py
pytest -vv tests/test_ut_decoder.py
pytest -vv tests/test_ut_regfile.py
```

### Load/Store unit tests
Purpose: validate the Load/Store Unit (LSU) across different configurations / pipeline depths.

Pytest file:
- `test_ut_loadstore.py`

Run:
```bash
pytest -vv tests/test_ut_loadstore.py
```

### Pipeline integration tests
Purpose: validate the (3-stage) pipeline integration (backend alone and together with fetch).

Pytest file:
- `test_integration_pipeline.py`

Run:
```bash
pytest -vv tests/test_integration_pipeline.py
```

### Core integration tests
Purpose: run the complete core in a testbench environment (16KB RAM @ 0) with the monitor port at `0x10000000..0x1fffffff`.

These tests execute `code/build/core-tests/*.hex` programs using `tb_core` and treat a run as PASS when the final monitor base write (`0x10000000`) equals `1`.
The discovery directory can be overridden with `BONFIRE_CORE_HEX_DIR`.

The test programs are documented in: [`../code/README.md`](../code/README.md)

Pytest file:
- `test_core.py`

Run:
```bash
pytest -vv tests/test_core.py
# tb_run-style monitor output
pytest -s -vv tests/test_core.py
```

Run a single program (examples):
```bash
pytest -s -vv tests/test_core.py --bonfire-hex code/build/core-tests/loadsave.hex
```

Notes:
- `wb_test.hex` is intentionally skipped (special case).
- `--bonfire-elf PATH` and `--bonfire-sig PATH` can be used with
  `--bonfire-hex` when a test needs an explicit ELF or signature path.

### SoC integration tests
Purpose: run the pure MyHDL SoC testbench that was historically available via
`tb_run.py --new_soc`.

Pytest file:
- `test_bonfire_core_soc_tb.py`

The test runs two variants:

- `code/build/soc/sim/led.hex` with the internal Wishbone dummy.
- `code/build/soc/sim/wishbone.hex` with the Wishbone master exposed and
  connected to `Wishbone_bfm`.

The firmware image can be overridden with `--bonfire-hex`.

Run:
```bash
pytest -vv tests/test_bonfire_core_soc_tb.py
pytest -vv tests/test_bonfire_core_soc_tb.py --bonfire-hex code/build/soc/sim/led.hex
```

## Waveforms

Tests that support MyHDL tracing accept these pytest options:

```bash
pytest tests/test_debug_module.py::test_debug_module_jtag -s -vv --waveform
pytest tests/test_jtag_dtm.py::test_jtag_dtm -s -vv --waveform --vcd jtag_dtm_manual
```

If `--vcd` is omitted, each test uses a stable default basename and writes to
`waveforms/<default>.vcd`.

## General notes
- Some legacy testbenches emit VHDL conversion output into `./vhdl_gen/`.
- Waveforms are written into `./waveforms`.
- The RISC-V compliance suite uses `run_compliance.py` (via `run_compliance.sh`) directly, not pytest. See [COMPLIANCE.md](../COMPLIANCE.md).

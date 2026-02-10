# Tests (pytest + legacy mapping)

This directory contains the pytest-based test suite for bonfire-core.

It covers the same *test intents* that historically existed in the `tb_run.py` workflow:

- **Module unit tests** (ALU, shifter, decoder, regfile)
- **Load/Store unit tests** (LSU behavior/configurations)
- **Pipeline integration tests** (backend + fetch)
- **Core integration tests** (run full core against small programs)

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

These tests execute `code/build/*.hex` programs using `tb_core` and treat a run as PASS when the final monitor base write (`0x10000000`) equals `1`.

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
# by keyword (matches the parameter id, i.e. the hex path)
pytest -vv tests/test_core.py -k loadsave

# exact parameter id match
pytest -vv tests/test_core.py -k "code/build/loadsave.hex"

# with monitor output for a single program
pytest -s -vv tests/test_core.py -k loadsave
```

Notes:
- `wb_test.hex` is intentionally skipped (special case).

## General notes
- Some legacy testbenches emit VHDL conversion output into `./vhdl_gen/`.
- Waveforms are written into a per-test temporary directory.
- The RISC-V compliance suite uses `run_compliance.py` (via `run_compliance.sh`) directly, not pytest. See [COMPLIANCE.md](../COMPLIANCE.md).

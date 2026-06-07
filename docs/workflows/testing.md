# Testing

Bonfire Core uses a pytest-based test suite. This page describes the test
groups, how to run them, and where the test files live.

## Run everything

```bash
cd bonfire-core
. .venv/bin/activate
pytest
```

Or through the universal runner:

```bash
scripts/bonfire-core --all
```

## Test groups

### Module unit tests

Purpose: validate individual RTL modules in isolation.

| Pytest file | Module under test |
| --- | --- |
| `tests/test_ut_alu.py` | ALU |
| `tests/test_ut_barrel_shifter.py` | Barrel shifter |
| `tests/test_ut_decoder.py` | Decode stage |
| `tests/test_ut_regfile.py` | Register file |

Run:

```bash
pytest -vv tests/test_ut_alu.py
pytest -vv tests/test_ut_barrel_shifter.py
pytest -vv tests/test_ut_decoder.py
pytest -vv tests/test_ut_regfile.py
```

Via the runner:

```bash
scripts/bonfire-core --ut
```

### Load/Store unit tests

Purpose: validate the Load/Store Unit (LSU) across different configurations
and pipeline depths.

```bash
pytest -vv tests/test_ut_loadstore.py
```

### Pipeline integration tests

Purpose: validate the 3-stage pipeline (backend alone and together with
the fetch unit).

```bash
pytest -vv tests/test_integration_pipeline.py
```

### Core integration tests

Purpose: run the complete core in a testbench environment — 16 KiB RAM
at address `0x0` and a monitor port at `0x10000000`–`0x1fffffff`.

Each test executes a `code/build/core-tests/*.hex` program using `tb_core`
and treats the run as PASS when the final monitor base write (`0x10000000`)
equals `1`. The discovery directory can be overridden with
`BONFIRE_CORE_HEX_DIR`.

```bash
pytest -vv tests/test_core.py
# with monitor output
pytest -s -vv tests/test_core.py
```

Run a single program by keyword:

```bash
pytest -vv tests/test_core.py -k loadsave
pytest -s -vv tests/test_core.py -k "code/build/core-tests/loadsave.hex"
```

!!! note
    `wb_test.hex` is intentionally skipped by the normal core integration
    tests because it expects a Wishbone BFM / external target.

Via the runner:

```bash
scripts/bonfire-core --integration
```

### SoC integration tests

Purpose: run the pure MyHDL SoC testbench.

The test runs two firmware variants:

- `code/build/soc/sim/led.hex` with the internal Wishbone dummy.
- `code/build/soc/sim/wishbone.hex` with the Wishbone master exposed and
  connected to `Wishbone_bfm`.

The firmware image can be overridden with `BONFIRE_SOC_HEX`.

```bash
pytest -vv tests/test_soc_myhdl.py
```

### Extended SoC integration tests

Purpose: run the Extended SoC VHDL simulation through FuseSoC + GHDL.

Requires `ghdl` and `fusesoc` to be installed.

```bash
pytest -vv tests/test_extended_soc_fusesoc.py
```

The test supports both a global `ghdl` installation and the local OSS CAD
Suite environment (`source ~/opt/oss-cad-suite/environment` before running).

### OpenOCD remote bitbang tests

Purpose: validate the simulated GDB server / OpenOCD remote bitbang interface.

```bash
pytest -vv tests/test_openocd_remote_bitbang.py
```

!!! note
    These tests require `openocd` to be installed. If it is not found, the
    tests are skipped. They also require
    `code/build/debug-tests/endless.hex` to be present.

## Monitor port convention

Most core test programs use the testbench **monitor port**:

| Address | Meaning |
| --- | --- |
| `monitor + 0` (`0x10000000`) | Write `1` for success, write `0xffffffff` (−1) for failure |
| `monitor + 4` | Optional: additional diagnostics |
| `monitor + 0x200` | Optional: result log area |

Writes to the monitor range are reported to the console. A write to the
monitor base address terminates the testbench run.

## General notes

- Legacy testbenches may emit VHDL conversion output into `./vhdl_gen/`.
- Waveforms are written into per-test temporary directories.
- The RISC-V compliance suite uses `run_compliance.py` directly, not pytest.
  See [Compliance](../software/compliance.md).

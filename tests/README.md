# Tests (pytest + legacy mapping)

This directory contains the pytest-based test suite for bonfire-core.

It covers the same broad test intents that historically existed in the
`tb_run.py` workflow, but is now organized by execution level first:

- `pure/` — pure MyHDL/Python tests without HEX/ELF program loading
- `system/` — larger integration tests that load firmware images or exercise a fuller system path
- `conversion/` — VHDL conversion checks grouped by domain
- `fusesoc/` — FuseSoC packaging/build integration tests

For the legacy `tb_run.py` commands, see: [`../TB_RUN.md`](../TB_RUN.md)

## Run everything

```bash
cd bonfire-core
. .venv/bin/activate
pytest
```

## Test layout

```text
tests/
  pure/
    core/
    debug/
    uncore/

  system/
    core/
    debug/
    soc/

  conversion/
    core/
    debug/
    soc/
    uncore/

  fusesoc/
```

## Test groups

### Pure core tests
Purpose: validate individual core blocks and small pure-MyHDL integration paths without firmware images.

Pytest files:
- `tests/pure/core/test_alu.py`
- `tests/pure/core/test_barrel_shifter.py`
- `tests/pure/core/test_decoder.py`
- `tests/pure/core/test_disassemble.py`
- `tests/pure/core/test_divider.py`
- `tests/pure/core/test_loadstore.py`
- `tests/pure/core/test_pipeline.py`
- `tests/pure/core/test_regfile.py`

Run:
```bash
pytest -vv tests/pure/core
```

### Pure uncore tests
Purpose: validate standalone uncore blocks without firmware images.

Pytest files:
- `tests/pure/uncore/test_dbus_interconnect.py`
- `tests/pure/uncore/test_uart.py`

Run:
```bash
pytest -vv tests/pure/uncore
```

### Pure debug tests
Purpose: validate standalone debug/JTAG transport blocks without loading firmware.

Pytest files:
- `tests/pure/debug/test_jtag_dtm.py`

Run:
```bash
pytest -vv tests/pure/debug
```

### System core tests
Purpose: run the complete core in a testbench environment (16KB RAM @ 0) with the monitor port at `0x10000000..0x1fffffff`.

These tests execute `code/build/core-tests/*.hex` programs using `tb_core` and treat a run as PASS when the final monitor base write (`0x10000000`) equals `1`.
The discovery directory can be overridden with `BONFIRE_CORE_HEX_DIR`.

The test programs are documented in: [`../code/README.md`](../code/README.md)

Pytest file:
- `tests/system/core/test_core_programs.py`

Run:
```bash
pytest -vv tests/system/core/test_core_programs.py
# tb_run-style monitor output
pytest -s -vv tests/system/core/test_core_programs.py
```

Run a single program (examples):
```bash
pytest -s -vv tests/system/core/test_core_programs.py --bonfire-hex code/build/core-tests/loadsave.hex
```

Notes:
- `wb_test.hex` is intentionally skipped (special case).
- `--bonfire-elf PATH` and `--bonfire-sig PATH` can be used with
  `--bonfire-hex` when a test needs an explicit ELF or signature path.

### System SoC tests
Purpose: run the pure MyHDL SoC testbench that was historically available via `tb_run.py --new_soc`.

Pytest file:
- `tests/system/soc/test_soc_tb.py`

The test runs two variants:

- `code/build/soc/sim/led.hex` with the internal Wishbone dummy.
- `code/build/soc/sim/wishbone.hex` with the Wishbone master exposed and connected to `Wishbone_bfm`.

The firmware image can be overridden with `--bonfire-hex`.

Run:
```bash
pytest -vv tests/system/soc/test_soc_tb.py
pytest -vv tests/system/soc/test_soc_tb.py --bonfire-hex code/build/soc/sim/led.hex
```

### System debug tests
Purpose: run debug-stack tests that exercise firmware-loaded or host-tool-oriented integration paths.

Pytest files:
- `tests/system/debug/test_debug_module.py`
- `tests/system/debug/test_gdbserver_protocol.py`
- `tests/system/debug/test_openocd_remote_bitbang.py`

Run:
```bash
pytest -vv tests/system/debug
```

### Conversion tests
Purpose: validate that selected MyHDL designs convert cleanly to VHDL and, where applicable, pass follow-up GHDL analysis.

Pytest files:
- `tests/conversion/core/test_vhdl_conversion_core.py`
- `tests/conversion/debug/test_vhdl_conversion_debug.py`
- `tests/conversion/soc/test_vhdl_conversion_soc.py`
- `tests/conversion/uncore/test_uart_vhdl_conversion.py`

Run:
```bash
pytest -vv tests/conversion
```

### FuseSoC tests
Purpose: validate FuseSoC-level packaging/build and converted-VHDL execution paths.

Pytest files:
- `tests/fusesoc/test_core.py`
- `tests/fusesoc/test_dbus_interconnect.py`
- `tests/fusesoc/test_soc.py`

Run:
```bash
pytest -vv tests/fusesoc
```

## Waveforms

Tests that support MyHDL tracing accept these pytest options:

```bash
pytest tests/system/debug/test_debug_module.py::test_debug_module_jtag -s -vv --waveform
pytest tests/pure/debug/test_jtag_dtm.py::test_jtag_dtm -s -vv --waveform --vcd jtag_dtm_manual
```

If `--vcd` is omitted, each test uses a stable default basename and writes to
`waveforms/<default>.vcd`.

## General notes
- Some legacy testbenches emit VHDL conversion output into `./vhdl_gen/`.
- Waveforms are written into `./waveforms`.
- The RISC-V compliance suite uses `run_compliance.py` (via `run_compliance.sh`) directly, not pytest. See [COMPLIANCE.md](../COMPLIANCE.md).

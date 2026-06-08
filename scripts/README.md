# `scripts/bonfire-core` - Universal runner

`scripts/bonfire-core` is the recommended entry point for preparing the
Bonfire Core development environment and starting interactive simulation
servers.

The script no longer owns pytest test selection. Test selection, collection,
filtering, verbosity, and waveform generation are handled by pytest directly.

## Quick Start

```bash
scripts/bonfire-core --install
scripts/bonfire-core --pytest -- tests/test_ut_decoder.py -q
```

## Usage

```text
scripts/bonfire-core [OPTIONS] -- [PYTEST_ARGS...]

Pytest:
  --pytest          Run pytest. All arguments after "--" are passed to pytest.

Server modes:
  --gdbserver       Start the simulated GDB server instead of running pytest
  --openocd-bitbang Start the OpenOCD remote_bitbang JTAG/Core simulation server
  --hex PATH        Server HEX image to load
                    (default: code/build/debug-tests/endless.hex)
  --port N          Server TCP port (GDB default: first free port in 5500-5550,
                    OpenOCD bitbang default: 3335)
  --debug-trace     With --openocd-bitbang: print Debug Module/progbuf trace

Environment / venv:
  --install         Create/update ./.venv and install Python deps
  --keepenv         Do not activate ./.venv; keep current Python environment
                    (also via BONFIRE_CORE_KEEPENV=1)

Other:
  --help, -h        Show help
```

Exactly one mode must be selected: `--pytest`, `--gdbserver`, or
`--openocd-bitbang`.

## Pytest Workflows

List available tests:

```bash
scripts/bonfire-core --pytest -- --collect-only
```

Run one test:

```bash
scripts/bonfire-core --pytest -- tests/test_debug_module.py::test_debug_module_jtag -s -vv
```

Run unit tests:

```bash
scripts/bonfire-core --pytest -- \
  tests/test_ut_alu.py \
  tests/test_ut_barrel_shifter.py \
  tests/test_ut_decoder.py \
  tests/test_ut_divider.py \
  tests/test_ut_regfile.py \
  tests/test_ut_loadstore.py \
  tests/test_integration_pipeline.py
```

Run core tests:

```bash
scripts/bonfire-core --pytest -- tests/test_core.py -q
```

Run exactly one core HEX image:

```bash
scripts/bonfire-core --pytest -- \
  tests/test_core.py \
  --bonfire-hex code/build/core-tests/loadsave.hex \
  -s -vv
```

Optional ELF and signature paths are also pytest options:

```bash
scripts/bonfire-core --pytest -- \
  tests/test_core.py \
  --bonfire-hex code/build/core-tests/loadsave.hex \
  --bonfire-elf code/build/core-tests/loadsave.elf \
  --bonfire-sig signatures/loadsave.sig
```

## Waveforms

Waveform generation is a pytest feature:

```bash
pytest tests/test_debug_module.py::test_debug_module_jtag -s -vv --waveform
```

The same call through the runner:

```bash
scripts/bonfire-core --pytest -- \
  tests/test_debug_module.py::test_debug_module_jtag \
  -s -vv \
  --waveform
```

If `--vcd` is omitted, each test uses a stable default basename. For example,
`test_debug_module_jtag` writes:

```text
waveforms/debug_module_jtag.vcd
```

Use `--vcd` to choose an explicit basename or path:

```bash
scripts/bonfire-core --pytest -- \
  tests/test_jtag_dtm.py::test_jtag_dtm \
  -s -vv \
  --waveform \
  --vcd jtag_dtm_manual
```

Supported pytest waveform options:

```text
--waveform            Enable MyHDL waveform generation for tests that support it
--vcd NAME_OR_PATH    Optional waveform output basename/path
```

## GDB Server

Start the built-in Python GDB server:

```bash
scripts/bonfire-core --gdbserver --port 5500
```

This builds and loads `code/build/debug-tests/endless.hex` by default. Use a
different image with `--hex`:

```bash
scripts/bonfire-core --gdbserver \
  --hex code/build/debug-tests/endless.hex \
  --port 5500
```

Connect from GDB:

```bash
gdb-multiarch code/build/debug-tests/endless.elf
```

```gdb
set architecture riscv:rv32
target remote localhost:5500
```

## OpenOCD Remote Bitbang Server

Start the simulated core with a JTAG remote-bitbang server:

```bash
scripts/bonfire-core --openocd-bitbang --port 3335
```

Use a different image:

```bash
scripts/bonfire-core --openocd-bitbang \
  --hex code/build/debug-tests/endless.hex \
  --port 3335
```

Print Debug Module/progbuf trace output:

```bash
scripts/bonfire-core --openocd-bitbang --port 3335 --debug-trace
```

Example OpenOCD configuration:

```tcl
adapter driver remote_bitbang
remote_bitbang host localhost
remote_bitbang port 3335
transport select jtag

jtag newtap bonfire cpu -irlen 5 -expected-id 0x10e31913
target create bonfire.cpu riscv -chain-position bonfire.cpu

init
```

OpenOCD normally opens its GDB server on port `3333`. Connect with:

```gdb
set architecture riscv:rv32
target remote localhost:3333
```

## Environment Variables

### Toolchain

- `TOOLCHAIN_BIN` (default: `$HOME/opt/riscv-gnu-toolchain/bin`)
- `TARGET_PREFIX` (default: `riscv64-unknown-elf`)

`TARGET_PREFIX` can be either:

- a plain prefix, e.g. `riscv64-unknown-elf`
- a full path prefix, e.g. `/opt/riscv/bin/riscv64-unknown-elf`

### Python Environment

- `BONFIRE_CORE_KEEPENV=1` is equivalent to `--keepenv`

### Test Artifact Defaults

Some pytest tests still use these environment variables for artifact discovery:

- `BONFIRE_CORE_HEX_DIR` (default: `code/build/core-tests`)
- `BONFIRE_ELF_DIR` (default: `code/build/core-tests`)
- `BONFIRE_SIG_DIR` (default: `signatures`)

Waveforms are not configured through environment variables anymore; use pytest
`--waveform` and `--vcd`.

## Exit Codes

The runner exits non-zero on invalid options, missing venv unless `--keepenv`,
missing server HEX files, missing toolchain when a default server image must be
built, or failing pytest/server startup.

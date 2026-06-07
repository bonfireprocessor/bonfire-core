# Universal Runner

The recommended single entry point for day-to-day development is
`scripts/bonfire-core`.

## Responsibilities

The runner:

- activates the repo-local virtual environment (`.venv/`), unless told not to,
- ensures the RISC-V toolchain is available on `PATH`,
- runs selected pytest-based test groups (unit, pipeline, core HEX
  integration, SoC integration),
- can run exactly one core program (`--hex`),
- can start the simulated GDB server (`--gdbserver`).

!!! note
    The script always runs tests with normal pytest output capture. To see
    MyHDL/monitor prints, pass `-- -s` to pytest, or use `--hex` which
    already runs with `-s`.

## Quick start

```bash
cd bonfire-core
scripts/bonfire-core --install
scripts/bonfire-core --all
```

## Usage

```text
scripts/bonfire-core [OPTIONS] [-- PYTEST_ARGS...]

Test selection:
  --ut              Run unit + pipeline integration tests (pytest-based)
  --integration     Run core HEX integration tests (pytest-based)
  --all             Run all tests (default when no args are given)
  --gdbserver       Start the simulated GDB server instead of running pytest
  --port N          GDB server TCP port (default: first free port in 5500-5550)

Environment / venv:
  --install         Create/update ./.venv and install Python deps
  --keepenv         Do not activate ./.venv; keep current Python environment
                    (also via BONFIRE_CORE_KEEPENV=1)

Single core run (pytest-based):
  --hex PATH        Run exactly one HEX program via tests/test_core.py
                    With --gdbserver: HEX image to load
  --elf PATH        Optional ELF path (override)
  --sig PATH        Optional signature output path (override)
  --vcd PATH        Optional VCD output path (MyHDL appends .vcd automatically)

Other:
  --help, -h        Show help
```

## Common workflows

### Run everything

```bash
scripts/bonfire-core
# or explicitly
scripts/bonfire-core --all
```

### Unit + pipeline tests only

```bash
scripts/bonfire-core --ut
```

### Core integration tests only

```bash
scripts/bonfire-core --integration
```

### Run a single HEX program

```bash
scripts/bonfire-core --hex code/build/core-tests/loadsave.hex
```

Example output:

```text
eof at adr:0x118
Created ram with size 16384 words
...
Monitor write: @3055 10000000: 00000001 (1)
.
1 passed in 0.35s
```

### VCD output

```bash
scripts/bonfire-core --hex code/build/core-tests/loadsave.hex --vcd /tmp/loadsave.vcd
```

VCD also works for integration tests (combine with `-k` to trace a specific
test case):

```bash
scripts/bonfire-core --integration --vcd /tmp/loadsave.vcd -- -k loadsave -q
```

## Simulated GDB server

Build and start the simulated GDB server:

```bash
scripts/bonfire-core --gdbserver --port 1234
```

By default it loads `code/build/debug-tests/endless.hex`. If `--port` is
omitted, the server binds to the first free port in `5500-5550`.

Then connect from a second terminal:

```bash
riscv64-unknown-elf-gdb code/build/debug-tests/endless.elf
```

Inside GDB:

```gdb
target remote 127.0.0.1:1234
```

Direct module entry point (if you prefer to bypass the runner):

```bash
python -m gdbserver --hex code/build/debug-tests/endless.hex --port 1234
```

## Environment variables

### Toolchain

| Variable | Default | Description |
| --- | --- | --- |
| `TOOLCHAIN_BIN` | `$HOME/opt/riscv-gnu-toolchain/bin` | Path searched for the RISC-V toolchain binaries. |
| `TARGET_PREFIX` | `riscv64-unknown-elf` | Toolchain prefix; can be a plain prefix or a full path prefix. |

### Test artifacts

| Variable | Default | Description |
| --- | --- | --- |
| `BONFIRE_CORE_HEX_DIR` | `code/build/core-tests` | Where integration-test `.hex` files are discovered. |
| `BONFIRE_ELF_DIR` | `code/build/core-tests` | Where built `.elf` files are expected. |
| `BONFIRE_SIG_DIR` | `signatures` | Where signature files are written. |

### Environment control

| Variable | Equivalent option | Description |
| --- | --- | --- |
| `BONFIRE_CORE_KEEPENV=1` | `--keepenv` | Keep current Python environment instead of activating `.venv`. |

## Notes

- `--gdbserver` is a separate mode and cannot be combined with `--ut`,
  `--integration`, or pytest pass-through args.
- In `--gdbserver` mode, only `--hex` and `--port` are accepted from the
  run-specific options.
- The runner exits non-zero on missing toolchain, missing venv (unless
  `--keepenv`), or failing tests.

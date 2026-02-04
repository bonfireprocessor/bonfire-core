# RISC-V Compliance testing (bonfire-core)

This document describes how to run the **riscv-compliance** suite against **bonfire-core**.

Historically the compliance Makefiles called `tb_run.py` directly. The current workflow runs the simulator through **pytest** via:

- `tests/test_compliance_single.py` (runs exactly one compliance program)

`tb_run.py` remains useful for debugging, but it is not the recommended entry point for the compliance suite.

## How the compliance harness works

For each compliance test, the harness provides:

- an **ELF** (used to find `begin_signature` / `end_signature` symbols)
- a **HEX** file (32-bit hexdump loaded by the testbench)
- a **signature output** file path (written by the simulator)

`tests/test_compliance_single.py` reads these environment variables:

- `BONFIRE_COMPLIANCE_ELF`
- `BONFIRE_COMPLIANCE_HEX`
- `BONFIRE_COMPLIANCE_SIG`

It then runs `tb_core` and (if possible) dumps a signature via `tb/sim_monitor.py`.

If a test produces **no signature** (or an empty signature), the pytest adapter treats it as **ignored** and removes the empty file so that the compliance `verify.sh` prints `... IGNORE` and the overall run continues.

## Prerequisites

### bonfire-core Python environment

Create a venv in `bonfire-core/`:

```bash
cd bonfire-core
python -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install myhdl==0.11.51 pyelftools pytest
```

### RISC-V toolchain

You need a `riscv64-unknown-elf-*` toolchain with multilib support for `rv32i`.

### riscv-compliance repository

Use the bonfireprocessor fork (contains the `bonfire-core` target):

- <https://github.com/bonfireprocessor/riscv-compliance>

## Running riscv-compliance

From the **riscv-compliance** repo (recommended: use the wrapper script if available):

```bash
cd riscv-compliance
./scripts/run_bonfire_compliance.sh RISCV_TARGET=bonfire-core
```

Or directly via make (ensure the PYTHON points at bonfire-core venv):

```bash
cd riscv-compliance
make \
  RISCV_TARGET=bonfire-core \
  BONFIRE_CORE_ROOT=/path/to/bonfire-core \
  PYTHON=/path/to/bonfire-core/.venv/bin/python
```

To run only one ISA suite:

```bash
# rv32i
./scripts/run_bonfire_compliance.sh RISCV_TARGET=bonfire-core RISCV_ISA=rv32i

# rv32Zicsr
./scripts/run_bonfire_compliance.sh RISCV_TARGET=bonfire-core RISCV_ISA=rv32Zicsr
```

Parallel execution (if supported by the Makefiles):

```bash
./scripts/run_bonfire_compliance.sh PARALLEL=1 JOBS="-j8" RISCV_TARGET=bonfire-core
```

### Expected result

Typical successful summaries look like:

`rv32Zicsr`:

```text
Check               I-CSRRC-01 ... OK
Check              I-CSRRCI-01 ... OK
Check               I-CSRRS-01 ... OK
Check              I-CSRRSI-01 ... OK
Check               I-CSRRW-01 ... OK
Check              I-CSRRWI-01 ... OK
--------------------------------
OK: 6/6 RISCV_TARGET=bonfire-core RISCV_DEVICE=rv32Zicsr RISCV_ISA=rv32Zicsr
```

`rv32i` (some tests may be ignored when privilege/trap handling is not implemented):

```text
...
Check        I-MISALIGN_JMP-01 ... IGNORE
Check       I-MISALIGN_LDST-01 ... IGNORE
...
--------------------------------
OK: 48/48 RISCV_TARGET=bonfire-core RISCV_DEVICE=rv32i RISCV_ISA=rv32i
```

## Running a single compliance test manually

This is mainly for debugging the adapter.

1) Build the test in `riscv-compliance` (the Makefiles create files under `work/<isa>/`).
2) Run the pytest adapter with the proper env vars:

```bash
cd bonfire-core
. .venv/bin/activate

# Easiest: use the wrapper script and pass the base path (no extension)
scripts/run_compliance_single.sh /path/to/riscv-compliance/work/rv32i/I-ADD-01
# (runs: pytest -s -vv tests/test_compliance_single.py)

# (Equivalent manual invocation)
export BONFIRE_COMPLIANCE_ELF=/path/to/riscv-compliance/work/rv32i/I-ADD-01.elf
export BONFIRE_COMPLIANCE_HEX=/path/to/riscv-compliance/work/rv32i/I-ADD-01.elf.hex
export BONFIRE_COMPLIANCE_SIG=/path/to/riscv-compliance/work/rv32i/I-ADD-01.signature.output
pytest -q tests/test_compliance_single.py
```

## Notes

- Signature dumping relies on `pyelftools` to locate `begin_signature` / `end_signature` in the ELF.
- The compliance harness compares the generated signature against golden reference files.

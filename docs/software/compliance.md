# Compliance Testing

This page describes how to run the RISC-V compliance suite against Bonfire Core.

## How the compliance harness works

For each compliance test, the harness provides:

- an **ELF** (used to find `begin_signature` / `end_signature` symbols via
  `pyelftools`),
- a **HEX** file (32-bit hexdump loaded by the testbench),
- a **signature output** file path (written by the simulator).

`run_compliance.py` accepts these arguments:

```text
--hex <file.hex>
--elf <file.elf>
--sig <file.sig>
```

It runs `tb_core` directly and dumps a signature via `tb/sim_monitor.py`.

If a test produces no signature (or an empty signature), the simulator handles
it gracefully and the compliance `verify.sh` prints `... IGNORE`.

## Prerequisites

### Python environment

```bash
cd bonfire-core
python -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install myhdl==0.11.51 pyelftools pytest
```

Or use the universal runner:

```bash
scripts/bonfire-core --install
```

### RISC-V toolchain

A `riscv64-unknown-elf-*` toolchain with multilib support for `rv32i`.

### riscv-compliance repository

Use the bonfireprocessor fork, which contains the `bonfire-core` target:

```
https://github.com/bonfireprocessor/riscv-compliance
```

## Running the compliance suite

From the `riscv-compliance` repository (recommended):

```bash
cd riscv-compliance
./scripts/run_bonfire_compliance.sh RISCV_TARGET=bonfire-core
```

Or directly via make:

```bash
cd riscv-compliance
make \
  RISCV_TARGET=bonfire-core \
  BONFIRE_CORE_ROOT=/path/to/bonfire-core \
  PYTHON=/path/to/bonfire-core/.venv/bin/python
```

### Run a single ISA suite

```bash
# rv32i
./scripts/run_bonfire_compliance.sh RISCV_TARGET=bonfire-core RISCV_ISA=rv32i

# rv32Zicsr
./scripts/run_bonfire_compliance.sh RISCV_TARGET=bonfire-core RISCV_ISA=rv32Zicsr
```

### Parallel execution

```bash
./scripts/run_bonfire_compliance.sh PARALLEL=1 JOBS="-j8" RISCV_TARGET=bonfire-core
```

## Expected results

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

`rv32i` (some tests are ignored when privilege/trap handling is not implemented):

```text
...
Check        I-MISALIGN_JMP-01 ... IGNORE
Check       I-MISALIGN_LDST-01 ... IGNORE
...
--------------------------------
OK: 48/48 RISCV_TARGET=bonfire-core RISCV_DEVICE=rv32i RISCV_ISA=rv32i
```

## Running a single compliance test manually

1. Build the test in `riscv-compliance` (creates files under `work/<isa>/`).
2. Run the compliance script from the `bonfire-core` root:

```bash
. .venv/bin/activate

# Using the wrapper (activates venv automatically)
./run_compliance.sh \
  --hex /path/to/riscv-compliance/work/rv32i/I-ADD-01.elf.hex \
  --elf /path/to/riscv-compliance/work/rv32i/I-ADD-01.elf \
  --sig /path/to/riscv-compliance/work/rv32i/I-ADD-01.signature.output

# Or call Python directly
python run_compliance.py \
  --hex /path/to/riscv-compliance/work/rv32i/I-ADD-01.elf.hex \
  --elf /path/to/riscv-compliance/work/rv32i/I-ADD-01.elf \
  --sig /path/to/riscv-compliance/work/rv32i/I-ADD-01.signature.output

# Optional: enable verbose output
./run_compliance.sh --hex ... --elf ... --sig ... --verbose
```

## Notes

- Signature dumping relies on `pyelftools` to locate `begin_signature` /
  `end_signature` in the ELF.
- The compliance harness compares the generated signature against golden
  reference files.
- Tests requiring trap/CSR handling (e.g., `I-EBREAK-01`, `I-ECALL-01`,
  `I-MISALIGN_JMP-01`, `I-MISALIGN_LDST-01`) are ignored when the
  corresponding hardware features are not active.

## Relevant files

| File | Description |
| --- | --- |
| `run_compliance.py` | Compliance harness adapter (runs `tb_core`, dumps signature) |
| `run_compliance.sh` | Shell wrapper that activates the venv and calls `run_compliance.py` |
| `COMPLIANCE.md` | Original compliance documentation |

#!/usr/bin/env bash
set -euo pipefail

# Run a single riscv-compliance test via the bonfire-core pytest adapter.
#
# Usage:
#   scripts/run_compliance_single.sh /path/to/riscv-compliance/work/rv32i/I-ADD-01
#
# The argument is the *base path* without extension. The script will set:
#   BONFIRE_COMPLIANCE_ELF=<base>.elf
#   BONFIRE_COMPLIANCE_HEX=<base>.elf.hex
#   BONFIRE_COMPLIANCE_SIG=<base>.signature.output
#
# Notes:
# - This script intentionally does NOT activate a venv and does NOT cd into the repo.
#   Run it from the bonfire-core repo root with the venv already active.

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 /path/to/riscv-compliance/work/<isa>/<TEST-STUB>" >&2
  echo "Example: $0 /path/to/riscv-compliance/work/rv32i/I-ADD-01" >&2
  exit 2
fi

BASE="$1"

export BONFIRE_COMPLIANCE_ELF="${BASE}.elf"
export BONFIRE_COMPLIANCE_HEX="${BASE}.elf.hex"
export BONFIRE_COMPLIANCE_SIG="${BASE}.signature.output"

# Basic sanity checks (helpful error messages)
if [[ ! -f "$BONFIRE_COMPLIANCE_ELF" ]]; then
  echo "ERROR: missing ELF: $BONFIRE_COMPLIANCE_ELF" >&2
  exit 2
fi
if [[ ! -f "$BONFIRE_COMPLIANCE_HEX" ]]; then
  echo "ERROR: missing HEX: $BONFIRE_COMPLIANCE_HEX" >&2
  exit 2
fi
# Signature file is an output; ensure directory exists.
mkdir -p "$(dirname "$BONFIRE_COMPLIANCE_SIG")"

exec pytest -s -vv tests/test_compliance_single.py

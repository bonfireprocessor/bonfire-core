#!/usr/bin/env bash
set -euo pipefail

# Wrapper for run_compliance.py - activates venv and forwards all arguments
#
# This script is called by the RISC-V compliance test suite Makefile.
# It ensures bonfire-core's Python environment is active before running
# the compliance test simulator.
#
# Usage (from compliance suite):
#   ./run_compliance.sh --hex test.hex --elf test.elf --sig test.sig

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$SCRIPT_DIR"

# Activate venv if it exists
if [[ -d "$ROOT_DIR/.venv" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.venv/bin/activate"
fi

# Run compliance runner with all arguments
exec python "$ROOT_DIR/run_compliance.py" "$@"

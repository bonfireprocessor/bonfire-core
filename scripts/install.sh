#!/usr/bin/env bash
set -euo pipefail

# Install (or update) the Python virtual environment for bonfire-core.
#
# This script is intentionally simple and idempotent.
# It only manages the Python environment; toolchain install is out of scope.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"

PYTHON_BIN="${PYTHON_BIN:-python3}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "ERROR: python not found: $PYTHON_BIN" >&2
  exit 2
fi

if [[ ! -d "$VENV_DIR" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
. "$VENV_DIR/bin/activate"

python -m pip install -U pip
python -m pip install \
  myhdl==0.11.51 \
  pyelftools \
  pytest

echo "OK: installed venv at $VENV_DIR"
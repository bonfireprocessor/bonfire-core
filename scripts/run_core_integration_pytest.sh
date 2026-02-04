#!/usr/bin/env bash
set -euo pipefail

# Run the core HEX integration tests via pytest.
#
# This wrapper builds the code, keeps the generated ELFs, and runs only the
# pytest integration module that executes code/*.hex with the core testbench.
#
# It also passes paths for:
#   - ELF files (for signature symbol extraction)
#   - signature output files

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CODE_DIR="$ROOT_DIR/code"

TOOLCHAIN_BIN_DEFAULT="$HOME/opt/riscv-gnu-toolchain/bin"
TOOLCHAIN_BIN="${TOOLCHAIN_BIN:-$TOOLCHAIN_BIN_DEFAULT}"

# TARGET_PREFIX can be either:
# - a plain prefix like "riscv64-unknown-elf"
# - OR a full path prefix like "/opt/.../bin/riscv64-unknown-elf" (some environments expect this)
TARGET_PREFIX="${TARGET_PREFIX:-riscv64-unknown-elf}"

# Where the build will leave ELFs (relative to repo root by default)
BONFIRE_ELF_DIR_DEFAULT="code/build"
BONFIRE_ELF_DIR="${BONFIRE_ELF_DIR:-$BONFIRE_ELF_DIR_DEFAULT}"

# Where signature files will be written
BONFIRE_SIG_DIR_DEFAULT="signatures"
BONFIRE_SIG_DIR="${BONFIRE_SIG_DIR:-$BONFIRE_SIG_DIR_DEFAULT}"

PYTEST_ARGS=("${@:-}")

if [[ ! -d "$ROOT_DIR/.venv" ]]; then
  echo "ERROR: Python venv not found at $ROOT_DIR/.venv" >&2
  exit 2
fi

# Resolve gcc path. If TARGET_PREFIX already contains a path, don't prepend TOOLCHAIN_BIN.
GCC=""
if [[ "$TARGET_PREFIX" == */* ]]; then
  GCC="${TARGET_PREFIX}-gcc"
  TOOLCHAIN_BIN_RESOLVED="$(dirname "$TARGET_PREFIX")"
else
  GCC="$TOOLCHAIN_BIN/${TARGET_PREFIX}-gcc"
  TOOLCHAIN_BIN_RESOLVED="$TOOLCHAIN_BIN"
fi

if [[ ! -x "$GCC" ]]; then
  echo "ERROR: toolchain not found: $GCC" >&2
  echo "Hint: either set TARGET_PREFIX=riscv64-unknown-elf (and TOOLCHAIN_BIN=/path/to/bin)" >&2
  echo "      or set TARGET_PREFIX=/path/to/bin/riscv64-unknown-elf" >&2
  exit 2
fi

# Ensure toolchain bin dir is on PATH (needed when Makefiles call objdump/objcopy/etc.)
export PATH="$TOOLCHAIN_BIN_RESOLVED:$PATH"

mkdir -p "$ROOT_DIR/$BONFIRE_SIG_DIR"

pushd "$CODE_DIR" >/dev/null
# Force rebuild so the intermediate .elf files are created (make may consider
# .hex up-to-date and otherwise skip producing intermediates).
make -B all TARGET_PREFIX="$TARGET_PREFIX" KEEP_ELF=1
popd >/dev/null

pushd "$ROOT_DIR" >/dev/null
# shellcheck disable=SC1091
. .venv/bin/activate

export BONFIRE_ELF_DIR
export BONFIRE_SIG_DIR

# Run only the HEX integration tests by default.
pytest tests/test_core.py "${PYTEST_ARGS[@]}"
popd >/dev/null

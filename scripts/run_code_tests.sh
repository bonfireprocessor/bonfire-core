#!/usr/bin/env bash
set -euo pipefail

# Run bonfire-core code/*.hex programs in the MyHDL testbench.
#
# PASS criterion: last write to monitor base address (0x10000000) is 1.
# (This matches the convention used by loadsave.S and the updated basic_alu.S / simple_loop.S.)

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CODE_DIR="$ROOT_DIR/code"

TOOLCHAIN_BIN_DEFAULT="$HOME/opt/riscv-gnu-toolchain/bin"
TOOLCHAIN_BIN="${TOOLCHAIN_BIN:-$TOOLCHAIN_BIN_DEFAULT}"
TARGET_PREFIX="${TARGET_PREFIX:-riscv64-unknown-elf}"

SKIP_HEX=("wb_test.hex")

have() { command -v "$1" >/dev/null 2>&1; }

if [[ ! -d "$ROOT_DIR/.venv" ]]; then
  echo "ERROR: Python venv not found at $ROOT_DIR/.venv"
  echo "Hint: create it with: python3 -m venv .venv && . .venv/bin/activate && pip install myhdl==0.11.51 pyelftools"
  exit 2
fi

if [[ ! -x "$TOOLCHAIN_BIN/${TARGET_PREFIX}-gcc" ]]; then
  echo "ERROR: toolchain not found: $TOOLCHAIN_BIN/${TARGET_PREFIX}-gcc"
  echo "Set TOOLCHAIN_BIN or TOOLCHAIN_BIN_DEFAULT accordingly."
  exit 2
fi

export PATH="$TOOLCHAIN_BIN:$PATH"

pushd "$CODE_DIR" >/dev/null
make all TARGET_PREFIX="$TARGET_PREFIX"
popd >/dev/null

# Build a skip lookup table.
declare -A SKIP
for x in "${SKIP_HEX[@]}"; do
  SKIP["$x"]=1
done

pass=0
fail=0
skip=0

pushd "$ROOT_DIR" >/dev/null

# shellcheck disable=SC1091
. .venv/bin/activate

for f in "$CODE_DIR"/*.hex; do
  base="$(basename "$f")"

  echo "=== code/$base ==="

  if [[ -n "${SKIP[$base]:-}" ]]; then
    echo "SKIP"
    echo
    ((skip+=1))
    continue
  fi

  # Capture output for parsing + debugging.
  out="$(python tb_run.py --hex="code/$base" 2>&1)" || true
  echo "$out"

  last_line="$(grep -E 'Monitor write: .* 10000000:' <<<"$out" | tail -n 1 || true)"
  if [[ -z "$last_line" ]]; then
    echo "RESULT: FAIL (no monitor base write)"
    echo
    ((fail+=1))
    continue
  fi

  echo "$last_line"

  if grep -q '10000000: 00000001' <<<"$last_line"; then
    echo "RESULT: PASS"
    echo
    ((pass+=1))
  else
    echo "RESULT: FAIL"
    echo
    ((fail+=1))
  fi
done

popd >/dev/null

printf '\nSUMMARY: PASS=%d FAIL=%d SKIP=%d\n' "$pass" "$fail" "$skip"

if [[ "$fail" -gt 0 ]]; then
  exit 1
fi

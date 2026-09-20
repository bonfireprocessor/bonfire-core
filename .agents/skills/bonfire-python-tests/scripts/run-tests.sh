#!/usr/bin/env bash
# Run bonfire-core pytest while preserving complete output for later analysis.
set -uo pipefail

repo_root=$(git rev-parse --show-toplevel 2>/dev/null) || {
    echo "error: run from inside the bonfire-core Git worktree" >&2
    exit 2
}
cd "$repo_root"

reports_dir="temp/test-reports"
mkdir -p "$reports_dir"
timestamp=$(date -u +%Y%m%dT%H%M%SZ)
run_dir="$reports_dir/pytest-$timestamp-$$"
mkdir -p "$run_dir"
output="$run_dir/pytest-output.log"
report="$run_dir/failure-report.md"

if [[ -x .venv/bin/python ]]; then
    python_cmd=(.venv/bin/python)
else
    echo "error: missing project virtual environment: .venv/bin/python" >&2
    exit 2
fi

list_tests=false
if [[ ${1:-} == "--list" ]]; then
    list_tests=true
    shift
    # pytest.ini already adds -q; reset that addopt so a single -q prints node IDs.
    pytest_args=(-o addopts= --collect-only -q "$@")
elif (($#)); then
    pytest_args=("$@")
else
    pytest_args=(-vv)
fi

printf 'Running: '
printf '%q ' "${python_cmd[@]}" -m pytest "${pytest_args[@]}"
printf '\nComplete output: %s\n\n' "$output"

set +e
"${python_cmd[@]}" -m pytest "${pytest_args[@]}" 2>&1 | tee "$output"
pytest_status=${PIPESTATUS[0]}
set -e

if (( pytest_status == 0 )); then
    if [[ $list_tests == true ]]; then
        printf '\nTest collection succeeded (no tests were executed). Complete output retained at: %s\n' "$output"
    else
        printf '\npytest passed (exit 0). Complete output retained at: %s\n' "$output"
    fi
    exit 0
fi

# Keep a useful initial report even if no agent is available to perform the
# test-specific investigation required by SKILL.md.
{
    printf '# bonfire-core pytest failure report\n\n'
    printf -- '- UTC timestamp: `%s`\n' "$timestamp"
    printf -- '- Command: `'
    printf '%q ' "${python_cmd[@]}" -m pytest "${pytest_args[@]}"
    printf '`\n- Pytest exit status: `%d`\n' "$pytest_status"
    printf -- '- Complete raw output: `%s`\n\n' "$output"
    printf '## Extracted failure evidence\n\n```text\n'
    grep -E '^(FAILED |ERROR |E   |={3,} .* (FAILURES|ERRORS) .*=*|.*(AssertionError|Traceback \(most recent call last\)|ModuleNotFoundError|ImportError|FileNotFoundError|PermissionError|TimeoutError|subprocess\.CalledProcessError))' "$output" || true
    printf '```\n\n## Preliminary possible causes\n\n'
    if grep -qE 'ModuleNotFoundError|ImportError|No module named|command not found' "$output"; then
        printf -- '- **Dependency or tool unavailable (high confidence):** output contains an import/module/command-not-found error. Check `.venv`, `requirements.txt`, and required external tools.\n'
    fi
    if grep -qE 'No such file or directory.*(\.hex|\.elf)|FileNotFoundError.*(\.hex|\.elf)' "$output"; then
        printf -- '- **Missing generated program image (high confidence):** a HEX or ELF input is absent. System tests normally require the `code/build` preparation described in CI.\n'
    fi
    if grep -qiE 'ghdl|openocd|fusesoc' "$output"; then
        printf -- '- **Simulator/debug/FuseSoC environment (needs verification):** the output references GHDL, OpenOCD, or FuseSoC. Verify executable availability and its earlier diagnostic lines before attributing the failure to RTL.\n'
    fi
    if grep -qiE 'timeout|timed out' "$output"; then
        printf -- '- **Simulation timeout (needs verification):** inspect the complete log for the last DUT/monitor activity; it may be a deadlock, slow host tool, or an overly short timeout.\n'
    fi
    if grep -qE 'AssertionError|FAILED ' "$output"; then
        printf -- '- **Test assertion or behavioral regression (needs verification):** inspect every traceback and associated DUT/test source; do not assume a design regression when setup errors precede it.\n'
    fi
    printf '\n## Agent analysis\n\nPending: read the complete raw output and replace this with test-specific evidence, causes, and next steps.\n'
} > "$report"

printf '\npytest failed (exit %d).\nRaw output: %s\nFailure report: %s\n' "$pytest_status" "$output" "$report" >&2
exit "$pytest_status"

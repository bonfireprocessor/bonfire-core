---
name: bonfire-python-tests
description: Runs and thoroughly analyzes the bonfire-core Python pytest suite. Use for executing pytest, investigating failures, and producing an untracked failure report with errors and likely causes.
---

# bonfire-core Python tests

Run this skill from the repository root. It executes pytest with verbose output, preserves the complete console output, and, only on failure, creates a timestamped report below `temp/test-reports/`. That directory is ignored by Git.

## Run the suite

Use the project virtual environment when it exists:

```bash
.agents/skills/bonfire-python-tests/scripts/run-tests.sh
```

Pass pytest selectors or options through to limit or repeat an investigation:

```bash
.agents/skills/bonfire-python-tests/scripts/run-tests.sh tests/pure/core/test_alu.py -x
.agents/skills/bonfire-python-tests/scripts/run-tests.sh -m diagnostic tests/system/debug/test_openocd_remote_bitbang.py
```

The default command is `python -m pytest -vv`; `pytest.ini` supplies `tests` as the test root. Do not use `-x` for the initial complete-suite run: all failures and their output are needed.

## Run selections, groups, and waveforms

All arguments other than the skill's `--list` action are passed through to pytest, so execute one node ID, a file, a directory, or a `-k`/`-m` selection directly:

```bash
# Default: verbose output; one exact test
.agents/skills/bonfire-python-tests/scripts/run-tests.sh tests/pure/core/test_pipeline.py::test_pipelined_backend[True]

# A test group with concise console output
.agents/skills/bonfire-python-tests/scripts/run-tests.sh -q tests/pure/core

# All system-core parametrizations whose name denotes a four-stage pipeline
.agents/skills/bonfire-python-tests/scripts/run-tests.sh tests/system/core -k 'pipeline4 or 4-stage'

# A supporting MyHDL test with a named waveform
.agents/skills/bonfire-python-tests/scripts/run-tests.sh -s tests/pure/debug/test_jtag_dtm.py --waveform --vcd jtag_dtm_manual
```

`-vv` requests verbose pytest output (and is the default); `-q` requests concise output. The script still records the full output in either mode. `--waveform` works only for tests that implement the project's waveform fixture. Without `--vcd`, supported tests write their default VCD below `waveforms/`; a relative `--vcd NAME` also resolves below `waveforms/`. For multiple tests, do not force one shared `--vcd` basename because files can overwrite each other. Waveform-enabled runs should be sequential unless output names and working directories are known to be isolated.

## Natural-language requests

Interpret free-text requests as a test-selection and execution request, not as text to pass literally to pytest. First use `--list` when the requested name/configuration is ambiguous, then run the resolved node IDs, paths, markers, or `-k` expression. State the resolved pytest command before running it if the interpretation could change coverage.

Examples of intended mappings:

- “Führe alle Core Tests mit 4-stufiger Pipeline aus und poste das Ergebnis” → `tests/system/core -k 'pipeline4 or 4-stage'`. This includes interlocked and bypass variants whose collected node IDs identify a four-stage configuration.
- “Führe den ALU-Test ohne verbose Ausgabe aus” → `-q tests/pure/core/test_alu.py`.
- “Erzeuge ein Waveform für den JTAG-DTM-Test” → `-s tests/pure/debug/test_jtag_dtm.py --waveform`, plus a unique `--vcd` name when requested.

After every execution, read the complete captured output and post the command, selected/collected count, pass/fail/skip/xfail counts, warnings, waveform paths (when requested), and the failure-report path if one was generated. Never describe a selection as “all” when pytest reports deselected tests outside the requested configuration.

## List available tests

When asked which tests exist, collect rather than execute them:

```bash
.agents/skills/bonfire-python-tests/scripts/run-tests.sh --list
```

The command prints pytest node IDs, one per line. Optional selectors follow `--list`, for example `--list tests/system/core` or `--list -m diagnostic`. Read the complete list, then present it grouped by its path hierarchy and include the exact node IDs needed for a targeted rerun. Do not claim that collection means the tests passed.

## Required analysis workflow

1. Wait for the script to finish and retain its exit status. A nonzero pytest result is a test failure, not a tool error to discard.
2. On success, read the complete captured output path printed by the script and summarize collection, pass/skip/xfail counts, warnings, and suspicious non-fatal output.
3. On failure, read **all** of both files printed by the script: `pytest-output.log` and `failure-report.md`. For a large output log, use successive reads with offsets until EOF; never infer the result from only its tail or pytest's short summary.
4. Inspect every failed test's traceback and the relevant source/test code. Distinguish a functional regression from environmental/preparation failures. Check the report's heuristic causes against the evidence and replace or append concrete, test-specific causes.
5. Update the existing timestamped `failure-report.md` (do not create a tracked report) with an `## Agent analysis` section containing: each failing node id, the decisive error/traceback location, likely cause and confidence, environment/tooling observations, and focused next steps. Preserve the raw-output reference and heuristic evidence.
6. Report the exact report path to the user. Never delete failure reports unless the user explicitly asks.

## Project-specific prerequisites and interpretation

- `.venv` is the intended environment; dependencies are in `requirements.txt`. If absent or broken, describe that as setup failure rather than modifying the environment without authorization.
- The CI matrix in `.github/workflows/tests.yml` shows required external tools. System, conversion, and FuseSoC tests may need GHDL, OpenOCD, and the RISC-V cross-toolchain; system tests also need built HEX programs under `code/build`.
- CI runs some groups separately and adds `pytest-xdist` only for `tests/system/core`. When a full local run fails during collection because `-n` is unavailable, this is not relevant unless `-n` was requested.
- For a reproducible targeted rerun, invoke this script with the failed node id and applicable options. Keep the original full-suite report intact.

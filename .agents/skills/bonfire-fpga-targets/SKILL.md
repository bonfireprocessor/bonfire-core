---
name: bonfire-fpga-targets
description: Build, simulate, customize, and analyze Bonfire Core FuseSoC FPGA targets. Use for ECP5 bitstreams/nextpnr reports, GHDL simulation targets, temporary board variants, and Bonfire SoC configuration parameters.
---

# Bonfire Core FuseSoC builds

Work from the repository root. `fusesoc-cores/bonfire-core-soc.core` is the
source of truth for target names and target settings. Read its relevant target
and its base/anchor before executing a build; do not invent devices, packages,
flags, or resource capacities.

## Prerequisites and non-destructive policy

Builds can take minutes and normal builds overwrite `build/bonfire-core-soc_0/<target>/`.
State the target, firmware selection, flow, and expected output directory
before rebuilding. Do not delete `build/`, modify the main worktree's core
file, or parallelize builds without explicit user approval.

For ECP5 targets, prepare the project environment:

```bash
test -x .venv/bin/python
test -x scripts/oss-cad-suite-launcher
test -d .tools/oss-cad-suite
. .venv/bin/activate
export EDALIZE_LAUNCHER="$PWD/scripts/oss-cad-suite-launcher"
command -v fusesoc
"$EDALIZE_LAUNCHER" yosys --version
"$EDALIZE_LAUNCHER" nextpnr-ecp5 --version
```

Board targets commonly require a HEX image. Build it if absent or if the user
requests a fresh firmware build:

```bash
make -C code clean all TARGET_PREFIX=riscv64-unknown-elf
```

A missing cross-toolchain, OSS CAD Suite, GHDL, or HEX is a setup failure, not
an RTL regression.

## Core-file model

`fusesoc-cores/bonfire-core-soc.core` is CAPI2 YAML with these relevant parts:

- `name` is the VLNV `::bonfire-core-soc:0` used in `fusesoc run`.
- `generators.gen_bonfire_core_soc` calls `generators/gen_soc.py`.
- `filesets` define dependencies, source files, constraints (LPF/XDC/SDC/ISF),
  and conditional files controlled by flags.
- `generate.soc_top` and `generate.soc_tb` supply default generator parameters.
- `targets` choose a flow/tool, filesets, flags, generator-parameter overrides,
  toplevel, and tool/flow options. YAML anchors such as `*target_icepizero` and
  `*target_ulx3s` are inherited settings; inspect both the child and anchor.

The SoC generator accepts only these configuration controls and SoC parameters:
`bram_adr_width`, `laned_memory`, `num_leds`, `led_active_low`,
`expose_wishbone_master`, `num_gpio`, `enable_uart1`, `enable_spi`, `num_spi`,
`enable_gpio`, `register_wishbone_dbus`, `debug`, `enable_jtag_debug`,
`debug_jtag_transport`, `inst_uart_only`, `uart_fifo_depth`, plus
`hexfile`, `extended_soc`, `pipeline_length`, `writeback_bypass`,
`enable_m_extension`, `jump_bypass`, `language`, `top_entity_name`,
`myhdl_entity_name`, `gentb`, `generation_kind`, `conversion_warnings`, and
`diagnostics_quiet`.

Use YAML booleans (`true`/`false`) for a temporary target. `pipeline_length`
may only be `3` or `4`; `writeback_bypass: true` requires a four-stage
pipeline. A custom three-stage target must explicitly set
`writeback_bypass: false`. The standard `soc_top` generator defaults
`enable_m_extension: true`, so a no-M variant must explicitly set
`enable_m_extension: false`. `extended_soc: true` selects the extended wrapper
and forces Wishbone-master exposure. `debug_jtag_transport` accepts only `native` or `ecp5_jtagg`. The ECP5 JTAGG
wrapper is selected only when `enable_jtag_debug: true`; that basic-SoC wrapper
cannot expose the Wishbone master.

## Normal ECP5 builds

Current ECP5 targets include `icepizero`, `icepizero_jtag`,
`icepizero_jtagg`, `icepizero_extended`, `icepizero_extended_jtagg`, `ulx3s`,
`ulx3s_extended`, `ulx3s_jtagg`, and `ulx3s_extended_jtagg`. Build an exact
name from the core file:

```bash
. .venv/bin/activate
export EDALIZE_LAUNCHER="$PWD/scripts/oss-cad-suite-launcher"
fusesoc run --target=icepizero_jtagg --flag=fw_monitor ::bonfire-core-soc:0
```

`fw_monitor` chooses a conditional monitor HEX where that target defines it;
omit it for the default HEX. Do not assume arbitrary flags are valid. ECP5
artifacts normally appear in `build/bonfire-core-soc_0/<target>/` and may
include `next.log`, `yosys.log`, `bonfire-core-soc_0.bit`, `.svf`, `.config`,
or timing JSON depending on target options.

## GHDL simulation targets

The current GHDL simulation targets are `sim`, `sim_extended`,
`sim_converted`, and `cmods7_extended_sim`. Read the target before execution:
`sim`/`sim_extended` need their documented HEX inputs and `sim_converted` uses
the converted testbench generator. Run them through FuseSoC, not by guessing a
GHDL command line:

```bash
. .venv/bin/activate
command -v fusesoc
ghdl --version
fusesoc run --target=sim ::bonfire-core-soc:0
fusesoc run --target=sim_extended ::bonfire-core-soc:0
```

FuseSoC's GHDL backend normally uses `build/bonfire-core-soc_0/<target>-ghdl/`
(for example `sim-ghdl`), rather than the ECP5 target directory. Run one target
at a time and retain complete output. A simulation is successful only when
FuseSoC/GHDL exits zero and no testbench assertion/failure evidence appears in
the complete log. `FireAnt` (Efinity), `cmods7`/`cmods7_extended` (Vivado),
and `synth-gowin` require their respective non-GHDL flows;
`cmods7_extended_sim` is the GHDL exception.

## Temporary custom variants

For a request such as “IcePiZero with a 3-stage pipeline and no M extension”,
use an **isolated detached Git worktree**, never a temporary edit in the main
worktree. This protects local changes and makes the exact variant reproducible.
Create it below ignored `temp/fpga-worktrees/`, based on the currently checked
out commit:

```bash
variant=icepizero_p3_nom
worktree="temp/fpga-worktrees/$variant-$(date -u +%Y%m%dT%H%M%SZ)"
git worktree add --detach "$worktree" HEAD
```

Inside that worktree, copy the selected base target into a new, uniquely named
target in `fusesoc-cores/bonfire-core-soc.core`. Preserve all base-target
settings (flow, LPF, top-level, HEX selection, flags, and generator settings),
then change only the requested generator parameters. Since YAML replacement of
the `generate` list is not a deep merge, the temporary target must contain the
complete `soc_top` parameter mapping, not merely the changed keys. For the
example it must explicitly contain:

```yaml
pipeline_length: 3
writeback_bypass: false
enable_m_extension: false
```

### Core-file edit procedure (mandatory)

Do **not** modify the main worktree's core file, and do not use `yq`, a
PyYAML round-trip, or another YAML serializer to rewrite it. Such tools can
remove comments, change formatting, or expand/lose YAML anchors and merges.
Use a precise, context-based text edit in the detached worktree; use YAML tools
only to validate the result.

`targets:` is a top-level mapping. Every target name must have exactly two
leading spaces and its properties four. A target name at column 0 is a new
CAPI2 top-level property, not a target; FuseSoC rejects it. Blank lines have
no YAML meaning and are optional.

```yaml
# Correct: both mappings are below their respective parent keys.
targets:
  icepizero_jtagg_nomuldiv:
    <<: *target_icepizero
    filesets: [icepizero_lpf, icepizero_top, scripts]
```

Before editing, inspect the final target in the core file and choose an exact,
unique text context within the existing `targets:` mapping. Insert the complete
new target there, never after the end of that mapping at document root. Keep
its name unique. Copy the selected target's complete `generate: - soc_top:`
mapping verbatim, then alter only requested parameters; do not rely on YAML
merge inheritance for that list.

Immediately after editing, review `git diff --check` and `git diff --
fusesoc-cores/bonfire-core-soc.core`. Validate both the YAML structure and the
FuseSoC CAPI2 schema before any build:

```bash
.venv/bin/python - <<'PY'
import yaml

path = "fusesoc-cores/bonfire-core-soc.core"
with open(path, encoding="utf-8") as stream:
    core = yaml.safe_load(stream)
allowed_top_level = {"CAPI=2", "name", "generators", "filesets", "generate", "targets"}
unexpected = set(core) - allowed_top_level
assert not unexpected, "Unexpected top-level key(s): " + ", ".join(sorted(unexpected))
assert "targets" in core and "icepizero_jtagg_nomuldiv" in core["targets"]
print("YAML structure OK")
PY
. .venv/bin/activate
fusesoc core show ::bonfire-core-soc:0
```

Replace `icepizero_jtagg_nomuldiv` in the assertion with the actual variant
name. The Python check detects a target accidentally placed at column 0;
`fusesoc core show` detects CAPI2 schema errors. If either fails, revert only
the temporary edit and correct it. Then review the relevant anchor and run the
requested target so the generator validates its parameters.

Build from the worktree using its own `.venv`, `.tools/oss-cad-suite`, and
firmware prerequisites (or explicitly provision them there). Record the
worktree path, base commit, complete temporary-target diff, command, and
artifact paths. Copy only requested final artifacts/reports out of the
worktree. Remove the worktree with `git worktree remove "$worktree"` only after
the user approves cleanup.

If the requested configuration cannot coexist with the selected target's
wrapper, constraints, or JTAG transport, stop and explain the exact generator
validation/HDL limitation rather than silently changing unrelated parameters.

## Analyze ECP5 results

Analyze the requested target directory, never the newest report from some other
target. Read all of `next.log` (in chunks until EOF) and inspect `yosys.log`
when needed. Use final `Device utilisation` entries (`TRELLIS_COMB`,
`TRELLIS_FF`, `TRELLIS_IO`, `DP16KD`, `MULT18X18D`, special blocks) rather than
the pre-packing utilization. For every `Max frequency for clock` line, report
achieved MHz, requested MHz, and PASS/FAIL.

A bitstream can exist despite a timing failure because some targets use
`--timing-allow-fail`; a successful process is not timing closure. Preserve
exact warnings/errors and distinguish setup, generator/Yosys, place/route, and
timing failures. For comparisons, use the same source revision, firmware,
tool versions, and seed where possible.

Write a persistent report only when requested or on failure, under ignored
`temp/fpga-reports/`. Include command, target/variant diff, Git revision, tool
versions, artifacts, full-log paths, measured resource/timing evidence, and
only evidence-supported causes.

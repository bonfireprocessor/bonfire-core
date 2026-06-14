# Naming Guide

This project uses more than one naming regime on purpose. The right convention depends on whether a name is derived from an external specification, participates in HDL conversion, or is plain Python structure code.

## Core principles

1. Preserve clarity against the relevant specification.
2. Avoid naming that becomes ambiguous after conversion to VHDL or Verilog.
3. Use normal Python naming rules for non-converted helper and framework code.
4. Prefer consistency within a local domain over forced global uniformity.

## 1. Specification-derived names

When a name comes directly from a specification, keep it close to the spec unless there is a strong readability reason not to.

Examples:
- `haltreq`
- `resumereq`
- `cmderr`
- `dpc`
- `progbuf`
- `regno`

Rationale:
- makes cross-checking against the RISC-V specs easier
- reduces mental translation when reading register fields and debug logic

## 2. Code that is converted to HDL

For names that are part of code converted to VHDL or Verilog, use `snake_case`.

This applies especially to:
- signals
- signal bundles and their fields
- helper functions used inside `@block`, `@always`, `@always_comb`, `@always_seq`, or `@instance` based logic
- names that will surface in generated HDL

Examples:
- `current_ip_i`
- `jump_dest_o`
- `abstract_command_state`
- `debug_control`
- `read_reg_data`

Rationale:
- VHDL is not case sensitive
- `camelCase` and `PascalCase` can collapse into ambiguous names after conversion
- `snake_case` maps cleanly to generated HDL and waveforms

### HDL port suffixes

The established suffix style should be kept:
- `_i` for inputs
- `_o` for outputs
- `_we`, `_ack`, `_err`, `_rd`, `_wr` where appropriate

Examples:
- `ack_i`
- `db_rd`
- `rd_adr_o`
- `wbm_ack_i`

## 3. Non-converted Python code

For Python code that does not participate in HDL conversion, use standard Python conventions.

### Classes
Use `PascalCase`.

Examples:
- `BonfireCoreTop`
- `DebugCSRBundle`
- `DebugDecodeController`

### Functions and methods
Use `snake_case`.

Examples:
- `create_instance`
- `read_reg`
- `write_csr`
- `dbus_to_wishbone`

### Constants
Use `UPPER_SNAKE_CASE`.

Examples:
- `JTAG_IR_WIDTH`
- `DEBUG_SPEC_VERSION`
- `EBREAK_INSN`

## 4. File names

Prefer `snake_case` for source file names.

Examples:
- `debug_module.py`
- `clk_driver.py`
- `sim_main_memory.vhd`

Rationale:
- matches Python conventions
- aligns with HDL-safe naming
- avoids mixed casing across platforms and tools

## 5. Historical code

Existing names do not need to be renamed mechanically.

Prefer this order:
1. follow this guide for new code
2. rename public or frequently used APIs when touching them anyway
3. avoid broad churn unless there is a clear benefit
4. preserve spec-derived names where the spec mapping matters

## 6. Practical recommendation

When choosing a name, ask:
1. Is this name defined by a spec?
2. Will this name appear in generated HDL?
3. If not, can I use normal Python style?

If the answer is:
- spec-derived -> stay close to the spec
- converted to HDL -> use `snake_case`
- plain Python structure code -> use Python conventions

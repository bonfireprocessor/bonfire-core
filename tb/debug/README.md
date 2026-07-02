# tb/debug

This directory contains debug-related Python modules and MyHDL testbenches used by the Bonfire simulation and verification flow.

## Module overview

### `debug_api.py`
Transport-independent RISC-V Debug Module API.

**Purpose**
- Defines the main API/signature class used to access the RISC-V Debug Module.
- Implements common Debug Module operations such as halt/resume, GPR access, CSR access, program buffer use, and memory access.
- Serves as the base class for all transport-specific debug access implementations.

**Used for**
- Any test scenario that should exercise Debug Module behavior independent of the transport details.
- Shared functionality for direct DMI, native JTAG, and ECP5 JTAGG access paths.

---

### `dmi_api.py`
Direct DMI debug API.

**Purpose**
- Connects the transport-independent debug API directly to the simulated DMI bundle.
- Bypasses any serial transport encoding.

**Used for**
- Fast Debug Module tests that focus on register behavior, abstract commands, ndmreset, and core/debug interaction.
- GDB server simulation paths that directly drive the DMI interface.

---

### `jtag_api.py`
Native JTAG debug API.

**Purpose**
- Implements TAP-level stimulus for the standard RISC-V JTAG DTM.
- Handles IR/DR scans, DTMCS access, IDCODE access, and DMI transactions over JTAG.

**Used for**
- Tests that verify the native JTAG transport.
- End-to-end debug scenarios where the transport itself is part of what is being validated.

---

### `ecp5_jtagg_api.py`
ECP5 JTAGG-oriented debug API.

**Purpose**
- Specializes the JTAG API for the ECP5-style frontend using `ER1`/`ER2`.
- Models the timing and scan behavior used by the simulated JTAGG transport path.

**Used for**
- Tests that verify the dedicated ECP5 JTAGG frontend.
- OpenOCD-facing or full debug scenarios that should exercise the JTAGG transport instead of the native JTAG DTM.

---

### `tb_jtag_dtm.py`
MyHDL testbench for the native JTAG DTM transport.

**Purpose**
- Provides the JTAG bus functional model (`JtagBFM`) and a focused MyHDL testbench for the native JTAG DTM.
- Verifies scan-register behavior, IDCODE, DTMCS, BYPASS, and DMI transactions for the standard transport.

**Used for**
- Focused unit/integration tests of `rtl/debug/jtag_dtm.py`.
- Transport-level checks without involving the full core debug flow.

---

### `tb_ecp5_jtagg.py`
MyHDL testbench for the ECP5 JTAGG transport.

**Purpose**
- Builds a focused MyHDL testbench around the ECP5 JTAGG client and TAP emulator.
- Verifies `ER1`/`ER2` mapping, DTMCS behavior, and DMI access through the JTAGG-oriented frontend.

**Used for**
- Focused unit/integration tests of `rtl/debug/ecp5_jtagg_client.py` and `rtl/debug/ecp5_jtagg_tap.py`.
- Transport-level verification of the ECP5 path without needing the full SoC debug setup.

---

### `tb_debug_module.py`
MyHDL system testbench for the full debug-module path.

**Purpose**
- Instantiates the Bonfire core together with RAM, monitor logic, and the selected debug transport.
- Supports direct DMI, native JTAG, and ECP5 JTAGG driven debug scenarios.

**Used for**
- End-to-end Debug Module tests such as halt/resume, register access, memory access, abstract commands, and ndmreset behavior.
- Full-system debug verification where both the transport and the core-side debug implementation matter.

---

### `__init__.py`
Convenience re-export module.

**Purpose**
- Re-exports the main debug API classes for simple imports.

**Used for**
- Import stability and cleaner call sites such as `from tb.debug import DmiDebugAPI`.

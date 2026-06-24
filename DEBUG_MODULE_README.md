# Bonfire Core Debug Stack (Technical README)

This document describes the current debug stack in **bonfire-core**:

- RISC-V Debug Module implementation (`rtl/debugModule.py`)
- JTAG Debug Transport Module (DTM) (`rtl/jtag_dtm.py`)
- OpenOCD remote_bitbang simulation server (`openocd_bitbang`)
- Integration of the debug path into the Bonfire core (`rtl/bonfire_core_top.py` + decode/fetch/backend path)

---

## 1. Architecture Overview

Current end-to-end debug path:

`GDB -> OpenOCD -> remote_bitbang TCP protocol -> JTAG DTM -> DMI signals -> Debug Module registers/state -> core decode/fetch control`

For direct simulation tests, the Debug Module can also be driven without JTAG via direct DMI stimulus.

The implementation targets **RISC-V Debug Spec 0.13** semantics in a pragmatic subset (single-hart focus, abstract command driven debug flow).

---

## 2. Debug Module (`rtl/debugModule.py`)

### 2.1 Main responsibilities

- Expose DMI-visible debug registers (`dmstatus`, `dmcontrol`, `hartinfo`, `abstractcs`, `abstractauto`, `command`, `dataN`, `progbufN`)
- Track hart state (`running` / `halted`)
- Accept halt/resume requests
- Launch and track abstract commands
- Provide command result and error signaling (`cmderr`)
- Store debug-visible control/state (e.g. `dpc`, `dcsr` fields)

### 2.2 Implemented register-level behavior

- **`dmstatus` (0x11):** reports running/halted, resumeack, authenticated, spec version, impbreak
- **`dmcontrol` (0x10):** handles halt request, resume request, ndmreset bit storage
- **`hartinfo` (0x12):** reports datacount and dscratch count from config
- **`abstractcs` (0x16):** reports `progbufsize`, `busy`, `cmderr`, `datacount`; supports write-1-to-clear for `cmderr`
- **`command` (0x17):** accepts access-register command type (subset)
- **`abstractauto` (0x18):** supports autoexec triggers for `dataN` and `progbufN`
- **`data0..dataN` (0x04+):** command input/output data registers
- **`progbuf0..1` (0x20/0x21):** up to 2 program buffer words (config dependent)

### 2.3 Abstract command support

Implemented command type:

- **Access Register** (`cmdtype=0`) subset

Supported behavior:

- 32-bit transfers (`aarsize=2`)
- GPR read/write via abstract command path
- Limited CSR access path for debug CSRs (`dpc`, `dcsr` mapping used by current logic)
- Optional `postexec` to execute program buffer after transfer
- `transfer=0` + `postexec=1` style execution flow

Program buffer execution:

- `progbuf_size` supports **1 or 2** entries
- Execution state machine uses `exec` / `exec2` / `wait_retire`
- Two-slot execution runs `progbuf1` after `progbuf0` unless `ebreak` stops sequencing

Autoexec support:

- `autoexecdataN` and `autoexecprogbufN` are implemented
- Used for repeated operations such as memory streaming through `data0`

### 2.4 Core interaction behavior

- Halt request captured in decode stage when an instruction is active
- On halt, current PC is stored into `dpc`
- Resume request triggers `dpc_jump` to restart execution from stored `dpc`
- While halted, decode can inject register write operations and progbuf instructions

---

## 3. JTAG DTM (`rtl/jtag_dtm.py`)

### 3.1 Main responsibilities

- Implement a JTAG TAP state machine
- Expose RISC-V debug JTAG instructions and DR behavior
- Translate DMI DR scans into `AbstractDebugTransportBundle` transactions

### 3.2 Implemented JTAG instructions

- **IDCODE** (`0x01`)
- **DTMCS** (`0x10`)
- **DMI** (`0x11`)
- **BYPASS** (`0x1F`)

Key constants:

- IR width: 5
- IDCODE: `0x10E31913`
- DTM version: 1
- Default IR map: `IRLEN=5`, `IDCODE=0x01`, `DTMCS=0x10`, `DMI=0x11`, `BYPASS=0x1F`
- Alternate ECP5-style IR map: `IRLEN=6`, `IDCODE=0x01`, `DTMCS=0x38`, `DMI=0x32`, `BYPASS=0x1F`

### 3.3 DTM/DMI behavior

- DMI scan format: `{address, data, op}` (LSB-first)
- Supports DMI operations:
  - NOP
  - READ
  - WRITE
- Read pipeline behavior implemented via internal request/response staging
- `dmireset` handling through DTMCS bit 16
- `dmistat` currently kept at OK under normal operation

### 3.4 Clock-domain handling

- External JTAG pins (`tck/tms/tdi/trstn`) are synchronized into system clock domain
- TAP transitions and DR/IR updates are evaluated using synchronized edge detection

---

## 4. OpenOCD remote_bitbang server (`openocd_bitbang`)

### 4.1 Components

- `remote_bitbang.py`: protocol server (OpenOCD remote_bitbang command handling)
- `sim_testbench.py`: full MyHDL simulation tying server + JTAG DTM + core + RAM
- `main.py`: CLI runner for hosting the simulation server
- `bonfire.cfg`: example OpenOCD configuration

### 4.2 Implemented protocol support

Supported remote_bitbang commands:

- Pin writes (`'0'..'7'`) for `TCK/TMS/TDI`
- TDO read (`'R'`)
- Reset writes (`'r'..'u'`) for TRST handling
- LED/blink-related commands (`B/b/Z/z/O/o`) are accepted/ignored safely
- Client quit (`'Q'`) with optional simulation stop behavior

### 4.3 Runtime and observability features

CLI options include:

- `--host`, `--port`
- `--hex`, `--ramsize`
- `--verbose` (protocol logging)
- `--observe-jtag` (TAP + scan tracing)
- `--debug-trace` (DMI/progbuf/abstract-command trace)
- `--vcd`
- `--exit-on-client-quit`

The debug trace monitor reports:

- DMI reads/writes
- Abstract command writes and state transitions
- Progbuf writes and execution
- Halt/resume transitions
- DBUS activity while halted

---

## 5. Debug Module Integration into the Core

### 5.1 Top-level integration

In `BonfireCoreTop`:

- Debug module logic is instantiated when `config.enableDebugModule` is true
- Core instance requires a `debugTransportBundle` in this mode
- DMI interface instance connects transport signals to debug register/state bundle

### 5.2 Pipeline integration

- Decode stage owns most debug command orchestration
- Fetch stage suppresses normal forward progress while hart is halted
- Backend jump output is OR-combined with debug `dpc_jump` recovery path
- Progbuf instructions are multiplexed into decode when halted + exec state active

### 5.3 Transport options used in tests

- **Direct DMI simulation** path (`DebugAPISim`) for fast, detailed debug-module checks
- **JTAG simulation** path (`JtagDebugAPISim` + `JtagDTM`) for full transport verification

---

## 6. Supported Features (Current State)

1. Single-hart debug halt/resume flow
2. DMI register map subset for core debug operation
3. Access-register abstract commands (32-bit) for GPR and limited CSR path
4. Program buffer execution with configurable size 1 or 2
5. `abstractauto` for data/progbuf autoexec triggers
6. JTAG TAP + IDCODE/DTMCS/DMI/BYPASS instruction support
7. OpenOCD-compatible remote_bitbang server for simulated JTAG connectivity
8. End-to-end simulation path up to OpenOCD target creation (`GDB/OpenOCD/JTAG/DTM/DM/Core`)

---

## 7. Missing or Incomplete Functionality

1. **Full RISC-V Debug Spec coverage is not implemented**
   - Implementation is a practical subset, not a complete 0.13 feature set.

2. **Abstract command coverage is incomplete**
   - `quick_access` command type is defined but not implemented.
   - Only 32-bit transfer size is accepted.
   - `aarpostincrement` is parsed but not functionally applied.

3. **CSR/debug register access scope is limited**
   - Current command decode path is tailored to core GPR + limited debug CSR handling.
   - No general CSR access framework for arbitrary CSR numbers.

4. **Potentially incomplete debug-module fields/flows**
   - Multi-hart selection/management flows are not present.
   - Authentication/challenge flows are not implemented beyond always-authenticated status bit.
   - Additional optional DM features (e.g. full system-bus access block) are not present.

5. **OpenOCD examination compatibility gaps remain**
   - Repository docs already note that OpenOCD target examination may still fail until remaining DM compatibility gaps are implemented.

6. **Tooling/runtime dependency caveat**
   - OpenOCD bitbang tests require generated debug HEX images (e.g. `code/build/debug-tests/endless.hex`), otherwise startup fails.

---

## 8. Practical Bring-up Notes

1. Build debug test images before running OpenOCD bitbang flows.
2. Start server:
   - `scripts/bonfire-core --openocd-bitbang --port 3335`
3. Connect OpenOCD using a remote_bitbang config equivalent to `openocd_bitbang/bonfire.cfg`.
4. Optionally enable:
   - `--observe-jtag` for TAP visibility
   - `--debug-trace` for abstract command/progbuf diagnostics

### 8.1 Alternate ECP5-style IR profile

The JTAG DTM also supports a configurable alternate IR mapping intended for an
ECP5/JTAGG-style transport while keeping the standard RISC-V DMI semantics:

- `DTMCS = 0x38`
- `DMI = 0x32`

OpenOCD can use this profile with the companion config:

- `openocd_bitbang/bonfire_ecp5_er.cfg`

The current repository scope only changes the IR codes. The actual FPGA-side
binding to the ECP5 `JTAGG` primitive is a separate integration step.

---

## 9. Relevant Source Files

- `rtl/debugModule.py`
- `rtl/jtag_dtm.py`
- `rtl/decode.py`
- `rtl/fetch.py`
- `rtl/simple_pipeline.py`
- `rtl/bonfire_core_top.py`
- `openocd_bitbang/main.py`
- `openocd_bitbang/sim_testbench.py`
- `openocd_bitbang/remote_bitbang.py`
- `openocd_bitbang/bonfire.cfg`
- `openocd_bitbang/bonfire_ecp5_er.cfg`
- `tb/tb_debug_module.py`
- `tb/tb_jtag_dtm.py`
- `tests/test_debug_module.py`
- `tests/test_jtag_dtm.py`
- `tests/test_openocd_remote_bitbang.py`
- `scripts/README.md`

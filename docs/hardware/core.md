# Core Architecture

Bonfire Core is a modular, configurable RISC-V processor implemented in
[MyHDL](http://www.myhdl.org/). The design targets FPGA implementation and is
validated through simulation-based testing (both pure MyHDL and GHDL).

## Design goals

- Implement the RV32I base ISA.
- Pass the RISC-V compliance suite.
- Run real C programs on FPGA targets.
- Reach clock frequencies comparable to the older Bonfire CPU design.
- Be extensible: optional debug module, future cache integration.

## Top-level structure: `BonfireCoreTop`

The main entry point is the `BonfireCoreTop` class in `rtl/bonfire_core_top.py`.
It represents the complete processor: fetch frontend plus execute backend.

```python
class BonfireCoreTop:
    def __init__(self, config: BonfireConfig = config.BonfireConfig()) -> None:
        self.config: BonfireConfig = config
        self.fetch: FetchUnit = FetchUnit(config=config)
        self.backend: SimpleBackend = SimpleBackend(config=config)
        ...
```

The hardware instance is created with `createInstance()`:

```python
core = BonfireCoreTop(config)
core_i = core.createInstance(
    ibus,              # DbusBundle — instruction fetch bus (read-only)
    dbus,              # DbusBundle — data bus (read/write)
    control,           # ControlBundle — control lines (interrupts, etc.)
    clock,             # bit signal — processor clock
    reset,             # bit signal — synchronous reset
    debug,             # DebugOutputBundle — simulation debug interface
    debugTransportBundle=None,  # optional RISC-V debug transport (DMI/JTAG)
)
```

### Ports

| Port | Direction | Type | Description |
| --- | --- | --- | --- |
| `ibus` | bidirectional | `DbusBundle` (read-only) | Instruction fetch bus. The core drives `en_o` and `adr_o`; the memory replies via `ack_i` and `db_rd`. |
| `dbus` | bidirectional | `DbusBundle` | Data bus for loads, stores, and CSR-triggered accesses. |
| `control` | in | `ControlBundle` | Control lines. Currently empty; reserved for future interrupt inputs. |
| `clock` | in | bit | Processor clock. All sequential logic is clocked on the rising edge. |
| `reset` | in | bit | Synchronous active-high reset. |
| `debug` | out | `DebugOutputBundle` | Simulation debug port: exposes the most recently committed result, register write address, and jump/branch status. Used by the testbench monitors. |
| `debugTransportBundle` | in | `AbstractDebugTransportBundle` | Optional. Required when `BonfireConfig.enableDebugModule` is `True`. Connects the RISC-V debug transport layer (e.g. OpenOCD remote bitbang). |

## Pipeline

Bonfire Core implements a **3-stage in-order pipeline**:

```
  ┌────────────┐     FetchInputBundle     ┌────────────┐
  │            │ ──────────────────────▶  │            │
  │   Fetch    │                          │   Decode   │
  │ (FetchUnit)│ ◀──────────────────────  │            │
  │            │   BackendOutputBundle    │            │
  └────────────┘  (jump_o / jump_dest_o)  └────┬───────┘
        │                                      │
        │ ibus                                 │ (internal decode bundle)
        ▼                                      ▼
   [Instruction                           ┌──────────┐
      Memory]                             │  Execute │
                                          │          │
                                     dbus │          │
                                    ──────▶          │
                                          └──────────┘
```

### Stage 1 — Fetch (`rtl/fetch.py`)

`FetchUnit` drives the instruction bus (`ibus`), tracks the program counter,
and handles jumps and branches:

- Fetches one instruction word per clock cycle.
- Buffers the fetched word and instruction pointer in a small FIFO before
  passing them to the backend as `FetchInputBundle`.
- Reacts to `jump_o` / `jump_dest_o` from the backend to redirect the PC.
- Optionally stalls when the debug module halts the hart.

### Stage 2 — Decode (`rtl/decode.py`)

The decode stage reads the instruction word and register file:

- Decodes the RISC-V opcode, function codes, immediate fields, and operand
  addresses (`rs1`, `rs2`, `rd`).
- Reads the register file (`rfPortA`, `rfPortB`).
- Produces a `DecodeBundle` that is registered and forwarded to the execute
  stage.
- Handles pipeline stalls when the execute stage is busy.

### Stage 3 — Execute (`rtl/execute.py`)

The execute stage carries out the decoded operation:

- ALU operations (arithmetic, logic, shifts) via `rtl/alu.py` and
  `rtl/barrel_shifter.py`.
- Branch evaluation and jump target calculation.
- Load/store via `rtl/loadstore.py`, which drives the data bus (`dbus`).
- CSR reads and writes via `rtl/csr.py`.
- Trap handling via `rtl/trap.py`.
- Writes the result back to the register file.

The execute stage can stall the pipeline by keeping `busy_o` high until a
multi-cycle operation (for example a bus transfer) completes.

### Register file (`rtl/regfile.py`)

`RegisterFile` provides two read ports (A and B) and one write port. It is a
standard synchronous register file with `x0` hardwired to zero.

## Configuration: `BonfireConfig`

All configurable aspects of the core are controlled through a `BonfireConfig`
object passed at construction time.

| Parameter | Default | Description |
| --- | --- | --- |
| `xlen` | `32` | Data and address width in bits. |
| `reset_address` | `0x0` | CPU reset vector (program counter after reset). |
| `shifter_mode` | `"pipelined"` | Barrel shifter implementation: `"pipelined"` uses a registered intermediate stage. |
| `RVC` | `False` | Compressed instruction extension (not yet implemented). |
| `jump_bypass` | `True` | Forward jump destination and branch result directly in the clock cycle after evaluation, reducing branch latency by one cycle. |
| `mem_write_early_term` | `False` | Allow combinatorial write-cycle termination on the `ack` signal. Reduces write latency by one cycle but creates a combinatorial path between `dbus.ack_i` and `execute.valid_o`. |
| `loadstore_outstanding` | `1` | Number of in-flight load/store operations. |
| `registered_read_stage` | `True` | Insert a register stage between the data bus and the LSU output. Improves timing at the cost of one extra cycle latency. |
| `enableDebugModule` | `False` | Instantiate the RISC-V debug module. Requires `debugTransportBundle` to be connected. |
| `num_dscratch` | `1` | Number of `dscratch` debug registers. |
| `numdata` | `1` | Number of debug data registers. |
| `dmi_adr_width` | `6` | DMI address width in bits (6 bits allows 64 debug registers). |
| `mcause_max` | `64` | Highest supported `mcause` trap reason. |

## Debug module

When `BonfireConfig.enableDebugModule` is `True`, `BonfireCoreTop` instantiates:

- `debugModule.DMI` — implements the Debug Module Interface (DMI) register map,
- `debugModule.DebugRegisterBundle` — registers shared between the DMI and the
  pipeline (halt, resume, program-buffer execution, data registers).

The debug transport (JTAG TAP, OpenOCD remote bitbang, etc.) connects through
`AbstractDebugTransportBundle`, which is passed to `createInstance()`. This
allows simulation-side or FPGA-side transports to plug in without changing the
core RTL.

The debug module can halt the hart, inject program-buffer instructions, and
access registers via abstract commands.

## Cache (experimental)

`rtl/cache/` contains an early cache implementation (`rtl/cache/cache.py`).
It is not yet wired into the standard SoC flow; its integration is a future
work item.

## Source files

| File | Description |
| --- | --- |
| `rtl/bonfire_core_top.py` | `BonfireCoreTop` — top-level wrapper that glues fetch and backend |
| `rtl/fetch.py` | `FetchUnit` — instruction fetch, PC management, jump control |
| `rtl/simple_pipeline.py` | `SimpleBackend`, `FetchInputBundle`, `BackendOutputBundle` — backend top |
| `rtl/decode.py` | `DecodeBundle` — instruction decode and register-file read |
| `rtl/execute.py` | `ExecuteBundle` — ALU, branch, load/store, CSR, trap dispatch |
| `rtl/alu.py` | Arithmetic/logic unit |
| `rtl/barrel_shifter.py` | Barrel shifter with optional pipeline register |
| `rtl/loadstore.py` | Load/store unit, drives `dbus` |
| `rtl/regfile.py` | 32×XLEN register file |
| `rtl/csr.py` | Control and status registers |
| `rtl/trap.py` | Trap/exception handling |
| `rtl/debugModule.py` | RISC-V debug module |
| `rtl/config.py` | `BonfireConfig` dataclass |
| `rtl/bonfire_interfaces.py` | `DbusBundle`, `ControlBundle`, `DebugOutputBundle`, `Wishbone_master_bundle` |
| `rtl/pipeline_control.py` | Pipeline stall/valid handshake helpers |

# Timing Note: Debug DPC Critical Path

## Context

The IcePi Zero yosys/nextpnr timing report showed the current longest path at
about 17.56 ns total delay, split into roughly 5.94 ns logic and 11.62 ns
routing. This is still below a 20 ns period, but it is close enough to be worth
tracking before increasing clock frequency or adding more debug logic.

The path does not appear to be a direct JTAG-DTM path. It is a normal core
control path that terminates in the debug controller because the debug module
now observes instruction retirement and updates `dpc`/`cause`.

## Likely MyHDL Path

Observed generated-VHDL names indicate this path:

1. DBus interconnect address decode and slave select:
   `rtl/uncore/dbus_interconnect.py`, `Master3Slaves.adrsel()` and `comb()`.

2. Load/store bus enable and stall feedback:
   `rtl/loadstore.py`, especially `bus.stall_i`, `bus_en`, and outstanding
   request handling.

3. Execute-stage busy/taken path:
   `rtl/execute.py`, `busy.next = alu.busy_o or ls.busy_o or csr.busy_o or jump_busy`.
   This feeds `PipelineControl.taken` in `rtl/pipeline_control.py`.

4. Branch/jump decision and target handling:
   `rtl/execute.py`, `jump_comb()`, using decode branch signals and ALU flags.

5. Debug retirement/DPC update:
   `rtl/execute.py`, `debug_retire_comb()`, then
   `rtl/debug_control.py`, `debug_module_seq()` updating `debugCSRUpdateBundle.dpc`
   and `debugCSRUpdateBundle.cause`.

The long CCU2C chain reported under a generated `decodebundle...branch_cmd...`
name is probably synthesized branch/decode arithmetic and comparison logic, not
just the boolean `branch_cmd` signal.

## Future Refactoring Ideas

- Register or otherwise decouple `instr_retired` / `instr_retire_dpc` before
  they enter the debug controller.
- Shorten the load/store stall to execute `taken` feedback path.
- Consider registering branch target and branch decision boundaries between
  decode and execute if higher clock targets become necessary.
- Recheck whether debug `dpc` update needs to be on the same cycle as
  retirement, or whether a one-cycle delayed debug-only path is acceptable.
- After each change, regenerate the IcePi Zero VHDL and compare nextpnr timing
  path names to confirm the path moved or shortened.

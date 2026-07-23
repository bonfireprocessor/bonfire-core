# ULX3S JTAGG Pipeline Comparison

Measurement from 2026-07-22 for `::bonfire-core-soc:0`, target `ulx3s_jtagg`,
with `fw_monitor`, ECP5-85K/CABGA381, speed grade 6, and the project-local
OSS-CAD toolchain (Yosys 0.67). The LPF constraint is 25 MHz, and every
configuration meets it.

## Results

| Configuration | Sysclk Fmax | LUT4 | TRELLIS_FF | `hazards.S` to monitor pass |
|---|---:|---:|---:|---:|
| 3 stages | **81.39 MHz** | 3,060 | 1,620 | 230 cycles |
| 4 stages, historical shared result, bypass enabled | 78.36 MHz | 3,017 | 1,654 | 230 cycles |
| 4 stages, historical shared result, bypass disabled | 81.07 MHz | 2,832 | 1,654 | 253 cycles |
| 4 stages, source registers, bypass enabled | **82.93 MHz** | 3,034 | 1,754 | 230 cycles |
| 4 stages, source registers, bypass disabled | 80.43 MHz | **2,740** | 1,754 | 253 cycles |

Compared with the three-stage pipeline:

- The historical shared-result implementation with bypass was 3.03 MHz
  slower (3.7%), used 43 fewer LUT4s and 34 more FFs, and added no cycles to
  the focused hazard test.
- The historical shared-result implementation without bypass was 0.32 MHz
  slower (0.4%), used 228 fewer LUT4s and 34 more FFs, and required 23
  additional cycles (10.0%) because of RAW interlocks.
- Source registers with registered one-hot selection cost 100 FFs compared
  with the former four-stage backend. The four data registers are driven
  directly by the functional units without an input-side load selection. In
  this single run, Fmax is 0.64 MHz lower without bypass and 4.57 MHz higher
  with bypass. Because the target does not use a fixed seed, even this larger
  improvement remains a single placement result and is not by itself a reason
  to change target defaults.

The Fmax figures are the final routed Sysclk values in `next.log`. Resource
figures come from the final Yosys cell statistics.

## Execution-Time Measurement

`code/core-tests/hazards.S` contains direct producer-consumer sequences for
the ALU, shifter, loads, stores, branches, CSR instructions, and JAL/JALR.
The MyHDL clock period is 10 time units, and monitor writes occur on rising
edges.

| Configuration | Monitor timestamp | Cycle count |
|---|---:|---:|
| 3 stages | `@2295` | 230 |
| 4 stages, bypass enabled | `@2295` | 230 |
| 4 stages, bypass disabled | `@2525` | 253 |
| 4 stages, source registers, bypass enabled | `@2295` | 230 |
| 4 stages, source registers, bypass disabled | `@2525` | 253 |

The cycle count is `(timestamp + 5) / 10`, because the first rising edge
occurs at time 5.

## Why Is Three-Stage Fmax Higher on ULX3S Than on IcePi Zero?

The comparison refers to the current measurement in
`TIMING_ICEPIZERO_JTAGG_PIPELINE_COMPARISON.md`: the same three-stage
architecture reaches 69.81 MHz on IcePi Zero and 81.39 MHz on ULX3S. Both
targets have the same structural bottleneck:

```text
SoC BRAM DOB -> LoadStoreUnit rdmux_out -> ls_result_o FF
```

| Target | Total delay | Logic | Routing |
|---|---:|---:|---:|
| IcePi Zero, ECP5-25K | 14.32 ns | 8.29 ns | 6.03 ns |
| ULX3S, ECP5-85K | 12.29 ns | 7.45 ns | 4.84 ns |

The 2.03 ns difference explains the Fmax gap. On the 85K device, both the
BRAM-to-LUT connection and the following load-formatting logic are placed and
routed more efficiently. The ULX3S path uses 1.19 ns less routing delay and
0.84 ns less logic delay.

This is not a different three-stage core architecture: both paths terminate
at the load/store result register. The material differences are the physical
target (85K instead of 25K), the resulting placement and packing, and the
slightly different platform-specific `monitor.hex` contents.

## Reproduction Conditions and Limitations

Each configuration was generated in a separate clean build root. Only
`pipeline_length` and `writeback_bypass` changed; JTAGG,
`jump_bypass: false`, firmware, and toolchain were identical within the ULX3S
comparison.

The source-register rows represent the current four-stage implementation; the
shared-result rows are historical comparison measurements. They were
generated in temporary build roots without changing the local target file.

The ULX3S target does not use a fixed nextpnr seed. These are therefore single
measurements, and small differences may be placement noise. Use a fixed seed
and repeated runs for reliable fine-grained comparisons.

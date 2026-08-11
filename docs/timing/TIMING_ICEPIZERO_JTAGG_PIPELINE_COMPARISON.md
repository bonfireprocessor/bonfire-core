# IcePi Zero JTAGG Pipeline Comparison

Updated measurement from 2026-07-23 for `::bonfire-core-soc:0`, target
`icepizero_jtagg`, with `fw_monitor`, ECP5-25K/CABGA256, and the
project-local OSS-CAD toolchain (Yosys 0.67). The target uses a 100 MHz LPF
constraint. All three current builds therefore report an expected timing
failure, although nextpnr still determines the maximum frequencies shown
below.

## Results

| Configuration | Sysclk Fmax | LUT4 | TRELLIS_FF | `hazards.S` to monitor pass |
|---|---:|---:|---:|---:|
| 3 stages | 69.81 MHz | 3,088 | 1,617 | 230 cycles |
| 4 stages, historical shared result, bypass enabled | 75.94 MHz | 3,037 | 1,651 | 230 cycles |
| 4 stages, historical shared result, bypass disabled | **83.56 MHz** | 2,868 | 1,651 | 253 cycles |
| 4 stages, source registers, bypass enabled | **84.49 MHz** | 2,927 | 1,751 | 230 cycles |
| 4 stages, source registers, bypass disabled | 82.90 MHz | **2,657** | 1,751 | 253 cycles |

Compared with the three-stage pipeline:

- The historical shared-result implementation with bypass gained 6.13 MHz
  (8.8%), used 51 fewer LUT4s and 34 more FFs, and added no cycles to the
  focused hazard test.
- The historical shared-result implementation without bypass gained
  13.75 MHz (19.7%), used 220 fewer LUT4s and 34 more FFs, and required 23
  additional hazard-test cycles (10.0%) because of RAW interlocks.
- The source-register implementation moves the result mux behind separate
  ALU, LSU, CSR, and jump-link registers. Four registered, mutually exclusive
  one-hot signals select the source. Compared with the former four-stage
  backend, this costs 100 FFs. Each data register is loaded directly from its
  functional unit on every clock; only the downstream mux uses the registered
  one-hot selection. In this run, Fmax is 8.55 MHz higher with bypass and
  0.66 MHz lower without bypass. Both configurations retain their previous
  hazard latency.

The Fmax figures are the final routed Sysclk values in `next.log`. Resource
figures come from the final Yosys cell statistics.

## Execution-Time Measurement

`code/core-tests/hazards.S` contains direct producer-consumer sequences for
the ALU, shifter, loads, stores, branches, CSR instructions, and JAL/JALR.
The MyHDL clock period is 10 time units, and monitor writes occur on rising
edges. The final monitor timestamps were:

| Configuration | Monitor timestamp | Cycle count |
|---|---:|---:|
| 3 stages | `@2295` | 230 |
| 4 stages, bypass enabled | `@2295` | 230 |
| 4 stages, bypass disabled | `@2525` | 253 |
| 4 stages, source registers, bypass enabled | `@2295` | 230 |
| 4 stages, source registers, bypass disabled | `@2525` | 253 |

The cycle count is `(timestamp + 5) / 10`, because the first rising edge
occurs at time 5.

## Reproduction Conditions and Limitations

Each configuration was generated in a separate clean build root and used the
same `monitor.hex` firmware, JTAGG target, and toolchain. Only the generator
parameters `pipeline_length` and `writeback_bypass` changed. The
source-register rows represent the current four-stage implementation; the
shared-result rows are historical comparison measurements. The builds ran in
temporary build roots separate from the local target file.

The target does not currently set a fixed nextpnr seed. These are therefore
single measurements, and small differences may be placement noise. The large
gap between both current four-stage configurations and the three-stage
reference is nevertheless clear. Within the source-register implementation,
bypass is 1.59 MHz faster in this run but uses 270 additional LUT4s; the
interlocked configuration requires 23 additional cycles for tightly coupled
RAW dependencies.

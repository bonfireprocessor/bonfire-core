# ECP5 JTAGG LED Demo

This FuseSoC core is a minimal hardware proof of concept for using the Lattice
ECP5 `JTAGG` primitive from a MyHDL design. It targets the Ice Pi Zero
(`LFE5U-25F-6MG256C`) and controls its five LEDs through the first JTAG user
register (ER1).

The core deliberately separates portable logic from the FPGA primitive. MyHDL
generates ordinary VHDL with an explicit JTAGG user interface. A static VHDL
top-level instantiates the ECP5 primitive and connects that interface. Generated
VHDL is never patched after conversion.

## Design hierarchy

```text
icepizero_jtagg_led_top                 static board top-level
|-- ecp5_jtagg_bridge                  static ECP5 primitive adapter
|   `-- JTAGG                          Lattice ECP5 hard JTAG primitive
`-- ecp5_jtagg_led_demo                MyHDL-generated user logic
    |-- 5-bit shift register           shifted through ER1
    `-- 5-bit LED register             loaded on JUPDATE
```

The source files have distinct responsibilities:

* `bonfire-ecp5-jtagg-led-demo.core` defines the Ice Pi Zero synthesis target.
* `generators/gen_ecp5_jtagg_led_demo.py` converts only the portable MyHDL LED
  logic and emits a generated FuseSoC core.
* `fpga/icepizero/icepizero_jtagg_led_top.vhdl` is the board wrapper and joins
  the generated logic to the primitive bridge.
* `vhdl/ecp5_jtagg_bridge.vhd` contains the single `JTAGG` instantiation.
* `fpga/icepizero/board.lpf` supplies the Ice Pi Zero package constraints.
* `scripts/template.tcl` imports VHDL through the GHDL Yosys plugin and runs
  `synth_ecp5`.

## JTAGG user interface

The primitive exposes the ECP5 hard JTAG TAP to fabric logic through these
signals:

| Direction from `JTAGG` | Signal | Purpose |
| --- | --- | --- |
| output | `JTCK` | JTAG clock for user-register logic |
| output | `JTDI` | serial data from the physical JTAG input |
| output | `JSHIFT` | shift-state indication |
| output | `JUPDATE` | update-state indication |
| output | `JRSTN` | active-low JTAG reset |
| output | `JCE1`, `JCE2` | user-register clock enables |
| output | `JRTI1`, `JRTI2` | user-register Run-Test/Idle indications |
| input | `JTDO1`, `JTDO2` | serial data returned by ER1 and ER2 |

The MyHDL bundle names are `jrt1` and `jrt2`; the static bridge maps them to
the primitive ports `JRTI1` and `JRTI2`.

The raw `TCK`, `TMS`, `TDI`, and `TDO` ports are part of the Yosys ECP5 cell
model but are not fabric connections in this design. The bridge leaves them
open. Its input declarations use the default value `'X'` so GHDL can elaborate
the component without creating constant-zero nets that nextpnr would attempt
to route into the hard JTAG block.

The `JTAGG` component is intentionally left unbound during GHDL elaboration.
This produces a GHDL binding warning, but preserves a cell named `JTAGG` for
`synth_ecp5`. Yosys and nextpnr then recognize it as the ECP5 hard primitive.
Adding an empty VHDL architecture for `JTAGG` is incorrect: synthesis may inline
or remove that empty design, taking all user logic driven by its outputs with
it.

## LED user register

The demo uses ER1, selected by ECP5 JTAG instruction `0x32`. While `JCE1` and
`JSHIFT` are asserted, each rising edge of `JTCK` shifts `JTDI` into a five-bit
register. `JTDO1` returns its least significant bit. A rising `JUPDATE` copies
the shift register to the LED register. ER2 is unused and `JTDO2` is held low.

The five shifted bits map directly to `led(4 downto 0)`. The Ice Pi Zero target
uses the existing board constraints and does not invert the LED vector.

## Building

Activate an OSS CAD Suite installation containing FuseSoC, GHDL, the GHDL
Yosys plugin, Yosys, nextpnr-ecp5, and Project Trellis:

```bash
source ~/opt/oss-cad-new/oss-cad-suite/environment
```

From the repository root, build the FPGA target:

```bash
fusesoc run --target=icepizero ::bonfire-ecp5-jtagg-led-demo:0
```

The principal outputs are written below:

```text
build/bonfire-ecp5-jtagg-led-demo_0/icepizero-trellis/
|-- bonfire-ecp5-jtagg-led-demo_0.bit
|-- bonfire-ecp5-jtagg-led-demo_0.json
|-- yosys.log
`-- next.log
```

## Testing on Ice Pi Zero

Load the generated bitstream into the FPGA, for example with
openFPGALoader:

```bash
openFPGALoader -b icepi-zero \
  build/bonfire-ecp5-jtagg-led-demo_0/icepizero-trellis/bonfire-ecp5-jtagg-led-demo_0.bit
```

The Ice Pi Zero connects its ECP5 JTAG port to the on-board FTDI FT231XQ. The
OpenOCD `ft232r` driver uses the UART handshake signals as synchronous JTAG
GPIOs. Close any program that has the FTDI serial port open, then start OpenOCD
with the board's signal mapping:

```bash
openocd \
  -c "adapter driver ft232r" \
  -c "adapter speed 1000" \
  -c "ft232r vid_pid 0x0403 0x6015" \
  -c "ft232r tck_num DSR" \
  -c "ft232r tms_num DCD" \
  -c "ft232r tdi_num RI" \
  -c "ft232r tdo_num CTS" \
  -c "ft232r trst_num RTS" \
  -c "ft232r srst_num DTR" \
  -c "ft232r restore_serial 0x0015" \
  -c "jtag newtap target tap -irlen 8 -expected-id 0x41111043" \
  -c "init"
```

Open a second terminal and connect to the OpenOCD command server:

```bash
telnet localhost 4444
```

Check the scan chain first:

```tcl
scan_chain
```

The `LFE5U-25F` must be reported with IDCODE `0x41111043`. OpenOCD should also
have printed a corresponding message during initialization:

```text
JTAG tap: target.tap tap/device found: 0x41111043
```

ER1 is selected by the 8-bit instruction `0x32`; its demo data register is five
bits wide. A direct write looks like this:

```tcl
irscan target.tap 0x32
drscan target.tap 5 0x15
```

For repeated tests, create a file named `led-test.tcl`:

```tcl
proc led {value} {
    irscan target.tap 0x32
    set previous [drscan target.tap 5 $value]
    puts "previous shift value: $previous"
}
```

Load the procedure from the OpenOCD Telnet console. Using a script avoids the
console treating each line of a multi-line procedure as a separate command:

```tcl
script /absolute/path/to/led-test.tcl
```

Exercise individual LEDs and useful patterns:

```tcl
led 0x00
led 0x01
led 0x02
led 0x04
led 0x08
led 0x10
led 0x15
led 0x1f
```

Bits 0 through 4 map directly to `led(0)` through `led(4)`. The value printed
by `led` is the previous contents shifted out through `JTDO1`, not a fixed
signature. ER2 (`0x38`) is unused by this demo and `JTDO2` is held low.

## Verifying synthesis

Successful command completion alone is not sufficient. Check that synthesis
did not optimize away the primitive or the user logic:

```bash
grep -E 'JTAGG|LUT4|TRELLIS_FF' \
  build/bonfire-ecp5-jtagg-led-demo_0/icepizero-trellis/yosys.log
grep 'JTAGG:' \
  build/bonfire-ecp5-jtagg-led-demo_0/icepizero-trellis/next.log
```

The design must contain one `JTAGG` cell as well as LUTs and flip-flops for the
shift and LED registers. nextpnr should report `JTAGG: 1/1`. A result with zero
LUTs or no `JTAGG` cell indicates that the primitive boundary was not preserved.

The automated FuseSoC smoke test runs the same complete flow when `yosys` and
`nextpnr-ecp5` are available. Without those FPGA tools it runs FuseSoC setup
only, so environments with FuseSoC and GHDL can still validate the generated
core and filesets:

```bash
OSS_CAD_SUITE_ENV=~/opt/oss-cad-new/oss-cad-suite/environment \
  pytest tests/fusesoc/test_ecp5_jtagg_led_demo.py -q
```

## Relationship to the Bonfire debug transport

This core validates primitive instantiation and JTAG USER-command data flow; it
does not contain the Bonfire CPU or RISC-V Debug Module. The Bonfire
`ecp5_jtagg` debug transport uses the same exported MyHDL bundle interface. A
board-specific static VHDL top-level is responsible for inserting this bridge
around a generated SoC, just as this demo top-level does around the LED logic.

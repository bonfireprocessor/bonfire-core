# Extended SoC

This document describes the current Extended SoC generation flow. It focuses on
the interaction between the FuseSoC generator in `fusesoc-cores/generators/gen_soc.py`
and the VHDL template in `fusesoc-cores/templates/soc_top.vhd`.

For a more detailed description of the generator implementation and parameter
normalization rules, see `soc/GEN_SOC_GENERATOR.md`.

The Extended SoC is not a separate MyHDL implementation. It is a generated VHDL
wrapper around the MyHDL-generated Bonfire Core SoC. The wrapper exposes the
MyHDL SoC's Wishbone master and connects it to VHDL peripherals such as UART,
GPIO, and SPI.

## Generation Flow

FuseSoC invokes the generator declared in `fusesoc-cores/bonfire-core-soc.core`:

```yaml
generators:
  gen_bonfire_core_soc:
    interpreter: python3
    command: generators/gen_soc.py
```

For each `generate:` block, FuseSoC writes an input YAML file and calls
`gen_soc.py`. The generator reads:

- `files_root`: normally `fusesoc-cores`,
- `parameters`: the parameters from the selected generate block,
- `vlnv`: the generated core name.

The generator then:

1. Converts `rtl/soc/bonfire_core_soc.py` from MyHDL to VHDL.
2. Optionally generates a VHDL wrapper from `fusesoc-cores/templates/soc_top.vhd`.
3. Optionally generates a VHDL testbench from `fusesoc-cores/templates/tb_soc.vhd`.
4. Writes a generated `.core` file that lists the generated VHDL files.

The generated files are placed in the FuseSoC generator cache below
`build/bonfire-core-soc_0/<target>/generator_cache/...`.

## Normal SoC vs Extended SoC

The generator has two modes controlled by the `extended_soc` parameter.

Without `extended_soc`:

- The MyHDL-generated entity uses `top_entity_name` directly.
- No VHDL wrapper is generated.
- The MyHDL SoC internally uses `wishbone_dummy` unless
  `expose_wishbone_master` is explicitly set.
- If `top_entity_name` and `myhdl_entity_name` are both set, they must have
  the same value because there is no wrapper entity.

With `extended_soc: true`:

- The MyHDL-generated entity defaults to `bonfire_core_myhdl_top`.
- The public top-level entity remains `top_entity_name`, usually
  `bonfire_core_soc_top`.
- `exposeWishboneMaster` is forced to true in `gen_soc.py`.
- `fusesoc-cores/templates/soc_top.vhd` is rendered into `<top_entity_name>.vhd`.
- `fusesoc-cores/templates/tb_soc.vhd` is rendered into `tb_<top_entity_name>.vhd`.

This means the Extended SoC has this hierarchy:

```text
board top-level
  -> generated VHDL wrapper: bonfire_core_soc_top
       -> MyHDL-generated SoC: bonfire_core_myhdl_top
            -> Bonfire CPU core
            -> BRAM
            -> native LED DBus register
            -> exposed Wishbone master
       -> VHDL Wishbone peripherals
```

## Generator Parameters

`gen_soc.py` maps FuseSoC parameters into a `soc_config` dictionary.

Common parameters:

| FuseSoC parameter | `soc_config` key | Meaning |
| --- | --- | --- |
| `bram_adr_width` | `bramAdrWidth` | BRAM depth as address width in 32-bit words |
| `laned_memory` | `lanedMemory` | Use byte-laned MyHDL RAM |
| `num_leds` | `numLeds` | Width of the LED output |
| `led_active_low` | `ledActiveLow` | LED output polarity |
| `expose_wishbone_master` | `exposeWishboneMaster` | Expose Wishbone instead of using internal dummy |
| `enable_jtag_debug` | `enableJtagDebug` | Enable the JTAG debug transport |
| `enable_debug_ndmreset` | `enableDebugNdmreset` | Enable Debug Module `ndmreset` reset control |
| `top_entity_name` | `topEntityName` | Public generated entity name |

Extended-wrapper-only parameters:

| FuseSoC parameter | `soc_config` key | Meaning |
| --- | --- | --- |
| `myhdl_entity_name` | `myhdlEntityName` | Name of the MyHDL-generated component |
| `num_gpio` | `numGpio` | Number of GPIO bits on the VHDL wrapper |
| `enable_uart1` | `enableUart1` | Enable UART1 in `bonfire_soc_io` |
| `enable_spi` | `enableSpi` | Enable SPI in `bonfire_soc_io` |
| `num_spi` | `numSpi` | Number of SPI ports |

When `extended_soc` is true, `gen_soc.py` forces:

```python
expose_wishbone_master = True
```

so the wrapper can connect the generated MyHDL SoC to external VHDL peripherals.

## `soc_top.vhd` Template

`fusesoc-cores/templates/soc_top.vhd` is a Python `str.format()` template. Placeholders such as
`{topEntityName}`, `{myhdlEntityName}`, `{numLeds}`, and `{enableSpi}` are replaced by
`gen_soc.py`.

The generated entity exposes board-facing ports:

- clock and reset: `sysclk`, `resetn`, `i_locked`, `o_resetn`,
- UART0 and UART1,
- SPI,
- GPIO,
- LEDs.

Internally it instantiates the MyHDL-generated component:

```vhdl
U_BONFIRE_CORE: {myhdlEntityName}
```

The MyHDL component exposes a Wishbone master using flattened MyHDL port names:

```vhdl
wb_master_wbm_cyc_o
wb_master_wbm_stb_o
wb_master_wbm_ack_i
wb_master_wbm_we_o
wb_master_wbm_adr_o
wb_master_wbm_db_o
wb_master_wbm_db_i
wb_master_wbm_sel_o
```

The wrapper maps those signals to an internal I/O Wishbone bus:

```text
io_cyc
io_stb
io_ack
io_we
io_sel
io_dat_wr
io_dat_rd
io_adr
```

The MyHDL-generated Wishbone address is 30 bits wide and represents
word-addressed DBus bits `[31:2]`. The wrapper maps the lower part into
`io_adr`:

```vhdl
io_adr(io_adr'range) <= adr_map(io_adr'length-1 downto 0);
```

`io_adr_high` is currently fixed to 25.

## Peripheral Selection

The VHDL wrapper has two mutually exclusive I/O implementations selected by the
generic `INST_UART_ONLY`.

### `INST_UART_ONLY = false`

The wrapper instantiates `bonfire_soc_io`:

```vhdl
Inst_bonfire_soc_io: entity work.bonfire_soc_io
```

This is intended to provide the integrated VHDL peripheral block:

- UART0,
- optional UART1,
- optional SPI,
- optional GPIO.

Its Wishbone slave interface is connected to the internal `io_*` bus.

### `INST_UART_ONLY = true`

The wrapper instantiates only `zpuino_uart`:

```vhdl
Inst_uart1: entity work.zpuino_uart
```

Despite the instance name, this is connected to the external UART0 pins
`uart0_txd` and `uart0_rxd`. This mode is mainly useful for UART-focused tests
and avoids instantiating the full `bonfire_soc_io` block.

The generic default in `soc_top.vhd` is currently:

```vhdl
INST_UART_ONLY : boolean := false
```

The generated VHDL testbench template `tb_soc.vhd` uses the same generated
default and passes the generic through to the DUT.

## Reset Handling

The MyHDL-generated SoC still receives:

- `resetn`,
- `i_locked`,
- `o_resetn`.

The wrapper also creates a local synchronous active-high `reset_sync` for the
VHDL peripheral block. It is derived from `resetn`:

```vhdl
process(sysclk, resetn)
```

`reset_sync` is used as `rst_i` or `wb_rst_i` for the VHDL peripherals.

## VHDL Testbench Template

`fusesoc-cores/templates/tb_soc.vhd` is also rendered with `gen_soc.py` when
`extended_soc` is enabled. The generated testbench:

- instantiates the generated Extended SoC top-level,
- provides a clock and reset,
- wires GPIO pads through a simple `gpio_pad` entity,
- loops SPI MISO back from MOSI,
- monitors LED and GPIO changes with `print`,
- captures UART0 TX using `tb_uart_capture_tx`,
- stops when the UART capture sees the stop marker byte `0x1A`.

This means the Extended SoC VHDL testbench is currently UART-output driven. It
does not stop based on LED activity.

## Current FuseSoC Targets

Targets that use the Extended SoC path include:

- `sim_extended`
  - `generate: [ soc_extended_sim ]`
  - includes `soc_io`
  - GHDL simulation target with top-level `tb_soc`

- `ulx3s_extended`
  - `generate: [ soc_extended ]`
  - uses extended ULX3S board top-level files
  - includes `soc_io`

- `icepizero_extended`
  - `generate: [ soc_extended_icepizero ]`
  - uses extended IcePi Zero board top-level files
  - includes `soc_io`

- `cmods7_extended`
  - `generate: [ soc_extended_cmods7 ]`
  - uses Vivado and CMOD-S7 board/IP files

- `cmods7_extended_sim`
  - simulation target for the CMOD-S7 extended top/testbench path

The generate block names use the corrected `soc_extended*` spelling.

## Dependencies

The Extended SoC wrapper depends on cores from the FuseSoC library configured in
`fusesoc.conf`:

```ini
[library.bonfire-library]
location = build/fusesoc_libraries/bonfire-library
sync-uri = https://github.com/bonfireprocessor/bonfire-library.git
sync-type = git
auto-sync = true
```

The relevant fileset is:

```yaml
soc_io:
  depend:
   - '>=::bonfire-soc-io:0'
   - ::bonfire-util:0
```

`INST_UART_ONLY` mode also requires `::zpuino-uart:0` through the library dependency
chain.

Always run FuseSoC from the project root so `fusesoc.conf` is used:

```bash
fusesoc list-cores
```

`::bonfire-core-soc:0` should be listed as a local core.

## Known Issues and Refactoring Notes

- The `extended_soc` path is a wrapper-generation mode, not a separate SoC
  implementation.
- The wrapper assumes a flattened MyHDL Wishbone master port naming scheme.
- `INST_UART_ONLY` chooses between full `bonfire_soc_io` and direct
  `zpuino_uart` for synthesis/debug isolation.
- The generated Extended SoC testbench stops on UART output, while the pure
  MyHDL SoC testbench stops on LED activity.
- `io_adr_high` is fixed in the template instead of being generated from a
  parameter.
- The wrapper has a debug Wishbone monitor, but it is controlled by a generic
  and is not currently integrated with pytest.
- The typo `extented` appears in generate block names and Python variables.

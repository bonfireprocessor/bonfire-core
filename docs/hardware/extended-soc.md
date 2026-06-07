# Extended SoC

The Extended SoC is a generated VHDL wrapper around the MyHDL-generated
Bonfire Core SoC. It exposes the MyHDL SoC's Wishbone master and connects it
to VHDL peripherals such as UART, GPIO, and SPI.

The Extended SoC is not a separate MyHDL implementation. It is produced by the
FuseSoC generator in `fusesoc-cores/generators/gen_soc.py` using the VHDL
template in `fusesoc-cores/templates/soc_top.vhd`.

## Design hierarchy

```
board top-level
  └─► generated VHDL wrapper: bonfire_core_soc_top
        ├─► MyHDL-generated SoC: bonfire_core_myhdl_top
        │       ├─► Bonfire CPU core
        │       ├─► BRAM (instruction + data)
        │       ├─► native LED DBus register
        │       └─► exposed Wishbone master
        └─► VHDL Wishbone peripherals
                ├─► UART0 (always enabled)
                ├─► optional UART1
                ├─► optional SPI
                └─► optional GPIO
```

## Generation flow

FuseSoC invokes the generator declared in `fusesoc-cores/bonfire-core-soc.core`:

```yaml
generators:
  gen_bonfire_core_soc:
    interpreter: python3
    command: generators/gen_soc.py
```

For each `generate:` block, FuseSoC writes an input YAML file and calls
`gen_soc.py`. The generator:

1. Converts `rtl/soc/bonfire_core_soc.py` from MyHDL to VHDL.
2. Generates a VHDL wrapper from `fusesoc-cores/templates/soc_top.vhd`.
3. Generates a VHDL testbench from `fusesoc-cores/templates/tb_soc.vhd`.
4. Writes a generated `.core` file that lists the generated VHDL files.

Generated files are placed in the FuseSoC generator cache below
`build/bonfire-core-soc_0/<target>/generator_cache/...`.

## Normal SoC vs Extended SoC

Without `extended_soc`:

- The MyHDL-generated entity uses `entity_name` directly.
- No VHDL wrapper is generated.
- The MyHDL SoC internally uses `wishbone_dummy` (unless
  `expose_wishbone_master` is explicitly set).

With `extended_soc: true`:

- The MyHDL-generated entity defaults to `bonfire_core_myhdl_top`.
- The public top-level entity remains `entity_name`, usually
  `bonfire_core_soc_top`.
- `exposeWishboneMaster` is forced to `True` in `gen_soc.py`.
- `fusesoc-cores/templates/soc_top.vhd` is rendered into `<entity_name>.vhd`.
- `fusesoc-cores/templates/tb_soc.vhd` is rendered into `tb_<entity_name>.vhd`.

## Generator parameters

`gen_soc.py` maps FuseSoC parameters into a `soc_config` dictionary.

### Common parameters

| FuseSoC parameter | `soc_config` key | Meaning |
| --- | --- | --- |
| `bram_adr_width` | `bramAdrWidth` | BRAM depth as address width in 32-bit words |
| `laned_memory` | `LanedMemory` | Use byte-laned MyHDL RAM |
| `num_leds` | `numLeds` | Width of the LED output |
| `led_active_low` | `ledActiveLow` | LED output polarity |
| `expose_wishbone_master` | `exposeWishboneMaster` | Expose Wishbone instead of using internal dummy |
| `entity_name` | `entity_name` | Public generated entity name |

### Extended-wrapper-only parameters

| FuseSoC parameter | `soc_config` key | Meaning |
| --- | --- | --- |
| `myhdl_entity_name` | `gen_core_name` | Name of the MyHDL-generated component |
| `num_gpio` | `numGpio` | Number of GPIO bits on the VHDL wrapper |
| `enable_uart1` | `enableUart1` | Enable UART1 in `bonfire_soc_io` |
| `enable_spi` | `enableSPI` | Enable SPI in `bonfire_soc_io` |
| `num_spi` | `numSPI` | Number of SPI ports |

## `soc_top.vhd` template

`fusesoc-cores/templates/soc_top.vhd` is a Python `str.format()` template.
Placeholders such as `{entity_name}`, `{gen_core_name}`, `{numLeds}`, and
`{enableSPI}` are replaced by `gen_soc.py`.

The generated entity exposes board-facing ports:

- clock and reset: `sysclk`, `resetn`, `i_locked`, `o_resetn`,
- UART0 and UART1,
- SPI,
- GPIO,
- LEDs.

Internally it instantiates the MyHDL-generated component:

```vhdl
U_BONFIRE_CORE: {gen_core_name}
```

The MyHDL component exposes a Wishbone master using flattened port names:

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

The wrapper maps those signals to an internal I/O Wishbone bus (`io_cyc`,
`io_stb`, `io_ack`, `io_we`, `io_sel`, `io_dat_wr`, `io_dat_rd`, `io_adr`).

The MyHDL-generated Wishbone address is 30 bits wide (word-addressed DBus bits
`[31:2]`). The wrapper maps the lower portion into `io_adr`:

```vhdl
io_adr(io_adr'range) <= adr_map(io_adr'length-1 downto 0);
```

`io_adr_high` is currently fixed to 25 in the template.

## Peripheral selection

The VHDL wrapper selects between two I/O implementations via the generic
`INST_UART_ONLY`.

### `INST_UART_ONLY = false` (default)

Instantiates `bonfire_soc_io`:

```vhdl
Inst_bonfire_soc_io: entity work.bonfire_soc_io
```

Provides the integrated VHDL peripheral block:

- UART0 (always),
- optional UART1,
- optional SPI,
- optional GPIO.

### `INST_UART_ONLY = true`

Instantiates only `zpuino_uart`:

```vhdl
Inst_uart1: entity work.zpuino_uart
```

Connected to the external UART0 pins. Mainly useful for UART-focused tests.

## Reset handling

The wrapper creates a synchronous active-high `reset_sync` for the VHDL
peripheral block:

```vhdl
process(sysclk, resetn)
```

`reset_sync` is used as `rst_i` / `wb_rst_i` for the VHDL peripherals.

## VHDL testbench template

`fusesoc-cores/templates/tb_soc.vhd` is rendered by `gen_soc.py` when
`extended_soc` is enabled. The testbench:

- instantiates the generated Extended SoC top-level,
- provides clock and reset,
- wires GPIO pads through a simple `gpio_pad` entity,
- loops SPI MISO back from MOSI,
- captures UART0 TX using `tb_uart_capture_tx`,
- stops when the UART capture sees the stop marker byte `0x1A`.

The Extended SoC testbench is UART-output driven. It does not stop based on LED
activity (unlike the pure MyHDL testbench).

## FuseSoC targets

| Target | Description |
| --- | --- |
| `sim_extended` | GHDL simulation with Extended SoC wrapper |
| `ulx3s_extended` | Lattice ECP5 (ULX3S) with `bonfire_soc_io` |
| `icepizero_extended` | iCE40 IcePi Zero with `bonfire_soc_io` |
| `cmods7_extended` | Vivado + CMOD-S7 with `bonfire_soc_io` |
| `cmods7_extended_sim` | Simulation target for the CMOD-S7 extended path |

## Running the Extended SoC simulation

Build the hello firmware:

```bash
make -C code soc SOC_APP=hello SOC_PLATFORM=sim TARGET_PREFIX=riscv64-unknown-elf
```

Run the GHDL simulation via FuseSoC:

```bash
fusesoc run --target=sim_extended ::bonfire-core-soc:0
```

Or run the pytest wrapper:

```bash
pytest -vv tests/test_extended_soc_fusesoc.py
```

## Building FPGA targets

Example non-extended build:

```bash
fusesoc run --target=icepizero ::bonfire-core-soc:0
```

Example extended build:

```bash
fusesoc run --target=ulx3s_extended ::bonfire-core-soc:0
```

Vivado example:

```bash
fusesoc run --target=cmods7_extended ::bonfire-core-soc:0
```

## Dependencies

The Extended SoC wrapper depends on cores from the FuseSoC library configured
in `fusesoc.conf`:

```ini
[library.bonfire-library]
location = build/fusesoc_libraries/bonfire-library
sync-uri = https://github.com/bonfireprocessor/bonfire-library.git
sync-type = git
auto-sync = true
```

The extended core also relies on the external `bonfire-library` for the
`bonfire-soc-io` peripheral block. You can add it locally with:

```bash
fusesoc library add --sync-type=local bonfire-library ../bonfire-library
```

Always run FuseSoC from the project root so `fusesoc.conf` is picked up:

```bash
fusesoc list-cores
```

`::bonfire-core-soc:0` should appear in the output.

## Hello firmware

The Extended SoC smoke-test firmware lives in `code/soc/apps/hello/main.c`. It
uses the local minimal runtime helpers (`code/soc/runtime/`) for UART, GPIO,
`printk`, and compact `snprintf`. The program writes output to UART0 and
terminates with the stop marker byte `0x1A`.

## Source files

| File | Description |
| --- | --- |
| `fusesoc-cores/generators/gen_soc.py` | FuseSoC generator that drives MyHDL→VHDL conversion and template rendering |
| `fusesoc-cores/templates/soc_top.vhd` | VHDL wrapper template for the Extended SoC |
| `fusesoc-cores/templates/tb_soc.vhd` | VHDL testbench template for the Extended SoC |
| `fusesoc-cores/bonfire-core-soc.core` | FuseSoC core description, target definitions, and generator declarations |
| `gen_soc.py` | Root-level compatibility wrapper for `gen_soc.py` |
| `tests/test_extended_soc_fusesoc.py` | pytest integration test for the Extended SoC simulation |
| `code/soc/apps/hello/main.c` | Extended SoC UART/GPIO smoke-test firmware |

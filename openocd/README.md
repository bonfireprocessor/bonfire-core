# Bonfire ECP5 JTAGG OpenOCD Setup

This directory contains the OpenOCD configuration for a Bonfire Basic SoC
running on an Ice Pi Zero and using the ECP5 hard JTAG port through `JTAGG`.
It accesses real hardware through the board's FTDI FT231XQ; it does not use the
Bonfire remote-bitbang server.

## Prerequisites

Build and load the `icepizero_jtagg` bitstream before starting OpenOCD:

```bash
source ~/opt/oss-cad-new/oss-cad-suite/environment
fusesoc run --target=icepizero_jtagg ::bonfire-core-soc:0
openFPGALoader -b icepi-zero \
  build/bonfire-core-soc_0/icepizero_jtagg-trellis/bonfire-core-soc_0.bit
```

OpenOCD must include the `ft232r` and RISC-V target drivers. Close terminal
programs that have the FTDI serial port open. On Linux, ensure that the current
user has USB access to device `0403:6015`, normally through an appropriate udev
rule.

## Starting OpenOCD

Run this command from the repository root:

```bash
openocd -f openocd/ecp5_jtagg.cfg
```

During initialization OpenOCD should report the Ice Pi Zero ECP5 IDCODE:

```text
JTAG tap: ecp5.tap tap/device found: 0x41111043
```

The configuration maps the ECP5 user instructions as follows:

```text
ER1  0x32  Bonfire DMI
ER2  0x38  Bonfire DTMCS
```

## Interactive Checks

Connect to the OpenOCD command server from another terminal:

```bash
telnet localhost 4444
```

Useful initial commands are:

```tcl
scan_chain
targets
halt
reg
resume
```

`scan_chain` must show `ecp5.tap` with IDCODE `0x41111043`. `targets` should
show `bonfire.cpu`. The `halt`, `reg`, and `resume` commands exercise the
Bonfire RISC-V Debug Module through the ECP5 JTAGG ER1/ER2 transport.

Stop OpenOCD with `shutdown` in the Telnet console or with Ctrl-C in the
OpenOCD terminal. The adapter configuration restores normal FTDI UART operation
when OpenOCD exits.

## VS Code Debugging

The following `.vscode/launch.json` configuration starts OpenOCD, connects GDB,
resets the target, and loads the monitor ELF. It deliberately leaves the CPU
halted after loading. It requires the Microsoft C/C++ extension (`cppdbg`).

The executable paths shown below are the default Homebrew paths on Apple
Silicon macOS. Adjust `miDebuggerPath` and `debugServerPath` for other systems.

```jsonc
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "GDB debug on FPGA: Ice Pi Zero monitor (OpenOCD/JTAGG)",
            "type": "cppdbg",
            "request": "launch",
            "program": "${workspaceFolder}/code/build/soc/icepizero/monitor.elf",
            "cwd": "${workspaceFolder}",
            "MIMode": "gdb",
            // cppdbg has no RISC-V value and otherwise aborts while parsing the ELF.
            // This only selects a 32-bit MIEngine code path; GDB still detects RISC-V.
            "targetArchitecture": "arm",
            "miDebuggerPath": "/opt/homebrew/bin/gdb",
            "miDebuggerServerAddress": "localhost:3333",
            "debugServerPath": "/opt/homebrew/bin/openocd",
            "debugServerArgs": "-f ${workspaceFolder}/openocd/ecp5_jtagg.cfg",
            "serverStarted": "Listening on port 3333 for gdb connections",
            "filterStderr": true,
            "customLaunchSetupCommands": [
                {
                    "text": "-file-exec-and-symbols ${workspaceFolder}/code/build/soc/icepizero/monitor.elf"
                },
                {
                    "text": "-target-select remote localhost:3333"
                },
                {
                    "text": "-interpreter-exec console \"monitor reset\""
                },
                {
                    "text": "-interpreter-exec console \"load\""
                }
            ],
            "launchCompleteCommand": "None"
        }
    ]
}
```

Keep the CPU Registers section in the VS Code debug view collapsed if the core
does not implement every CSR advertised by OpenOCD. Expanding it makes `cppdbg`
request all advertised registers and can noticeably slow down debugging.

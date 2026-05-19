#!/usr/bin/env python3
"""
RISC-V Compliance Test Runner for bonfire-core

This script runs a single bonfire-core simulation for RISC-V compliance testing.
It bypasses the pytest framework for minimal overhead and direct execution.

Called by: riscv-compliance test suite via wrapper script
Interface: Command-line arguments for hex, elf, and signature files

Usage:
    python run_compliance.py --hex <file.hex> --elf <file.elf> --sig <file.sig>

Arguments:
    --hex FILE   Required. Hex file containing test program
    --elf FILE   Required. ELF file for symbol/address info
    --sig FILE   Required. Output file for memory signature

Exit codes:
    0: Simulation completed successfully (signature written)
    1: Simulation failed or invalid arguments
    2: Missing required arguments

Note: This script does NOT check pass/fail of the test itself.
      The compliance suite compares the signature file to decide pass/fail.
"""

import sys
import argparse
from pathlib import Path

# Import testbench infrastructure
from tb import tb_core


def main():
    parser = argparse.ArgumentParser(
        description='Run bonfire-core simulation for RISC-V compliance testing'
    )
    parser.add_argument('--hex', required=True, help='Test program hex file')
    parser.add_argument('--elf', required=True, help='Test program ELF file')
    parser.add_argument('--sig', required=True, help='Output signature file')
    parser.add_argument('--vcd', help='Optional VCD waveform file for debugging')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Validate input files exist
    hex_path = Path(args.hex)
    elf_path = Path(args.elf)
    
    if not hex_path.exists():
        print(f"ERROR: Hex file not found: {args.hex}", file=sys.stderr)
        return 1
    
    if not elf_path.exists():
        print(f"ERROR: ELF file not found: {args.elf}", file=sys.stderr)
        return 1
    
    # Create signature directory if needed
    sig_path = Path(args.sig)
    sig_path.parent.mkdir(parents=True, exist_ok=True)
    
    if args.verbose:
        print(f"run_compliance.py - Running compliance test:")
        print(f"  HEX: {args.hex}")
        print(f"  ELF: {args.elf}")
        print(f"  SIG: {args.sig}")
        if args.vcd:
            print(f"  VCD: {args.vcd}")
    
    # Create and configure testbench
    tb = tb_core.tb(
        hexFile=args.hex,
        elfFile=args.elf,
        sigFile=args.sig,
        ramsize=16384,
        verbose=args.verbose
    )
    
    # Configure waveforms if requested
    if args.vcd:
        tb.config_sim(trace=True, filename=args.vcd, directory="./waveforms")
    else:
        tb.config_sim(trace=False)
    
    # Run simulation
    try:
        tb.run_sim(duration=20_000)
    except Exception as e:
        print(f"ERROR: Simulation failed: {e}", file=sys.stderr)
        tb.quit_sim()
        return 1
    
    tb.quit_sim()
    
    if args.verbose:
        print(f"Signature written to: {args.sig}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

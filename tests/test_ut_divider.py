"""
Unit tests for Divider (Non-Restoring Division)

Self-checking testbench for signed/unsigned division and remainder operations.
"""

from __future__ import annotations

import pytest
from myhdl import *

from rtl.divider import DividerBundle
from rtl import config

from .conftest import run_sim


def divider_testbench(signed_mode: bool = False, test_remainder: bool = False):
    """
    Self-checking testbench for the divider
    
    Args:
        signed_mode: Test signed division if True, unsigned if False
        test_remainder: Test remainder (modulo) if True, quotient if False
    """
    
    @block
    def testbench():
        # Clock and reset
        clk = Signal(bool(0))
        rst = ResetSignal(0, active=1, isasync=False)
        
        # Create divider bundle and instantiate
        div_bundle = DividerBundle(xlen=32)
        
        dut = div_bundle.divider(clk, rst)
        
        @always(delay(10))
        def clkgen():
            clk.next = not clk
        
        @instance
        def stimulus():
            # Set mode constants
            div_bundle.signed_i.next = signed_mode
            div_bundle.rem_i.next = test_remainder
            
            # Test cases: (dividend, divisor, expected_quotient, expected_remainder)
            if not signed_mode:
                # Unsigned division test cases
                test_cases = [
                    # Basic cases
                    (100, 10, 10, 0),
                    (17, 5, 3, 2),
                    (1000, 7, 142, 6),
                    (0, 10, 0, 0),
                    (10, 10, 1, 0),
                    
                    # Edge cases
                    (0xFFFFFFFF, 1, 0xFFFFFFFF, 0),
                    (0xFFFFFFFF, 2, 0x7FFFFFFF, 1),
                    (0x80000000, 2, 0x40000000, 0),
                ]
            else:
                # Signed division test cases
                test_cases = [
                    # Positive / Positive
                    (100, 10, 10, 0),
                    (17, 5, 3, 2),
                    
                    # Negative / Positive
                    (-100, 10, -10, 0),
                    (-17, 5, -3, -2),
                    
                    # Positive / Negative
                    (100, -10, -10, 0),
                    (17, -5, -3, 2),
                    
                    # Negative / Negative
                    (-100, -10, 10, 0),
                    (-17, -5, 3, -2),
                    
                    # Edge cases with sign
                    (0, 10, 0, 0),
                    (0, -10, 0, 0),
                    (-1, 1, -1, 0),
                    (1, -1, -1, 0),
                    
                    # Large signed values
                    (0x7FFFFFFF, 2, 0x3FFFFFFF, 1),  # Max positive / 2
                    (-2147483648, 2, -1073741824, 0),  # Min negative / 2 (0x80000000 / 2)
                ]
            
            # Convert signed test cases to proper two's complement representation
            def to_signed_32(val):
                """Convert signed int to 32-bit two's complement intbv"""
                if val < 0:
                    return intbv(val)[32:0]
                else:
                    return intbv(val)[32:0]
            
            # Reset
            rst.next = True
            yield clk.posedge
            rst.next = False
            yield clk.posedge
            
            print(f"\n{'='*60}")
            print(f"Testing Divider: {'SIGNED' if signed_mode else 'UNSIGNED'} "
                  f"{'REMAINDER' if test_remainder else 'QUOTIENT'}")
            print(f"{'='*60}\n")
            
            passed = 0
            failed = 0
            
            for dividend, divisor, expected_quot, expected_rem in test_cases:
                # Convert to proper representation for signed mode
                if signed_mode:
                    op1_val = to_signed_32(dividend)
                    op2_val = to_signed_32(divisor)
                    exp_q = to_signed_32(expected_quot)
                    exp_r = to_signed_32(expected_rem)
                else:
                    op1_val = intbv(dividend)[32:0]
                    op2_val = intbv(divisor)[32:0]
                    exp_q = intbv(expected_quot)[32:0]
                    exp_r = intbv(expected_rem)[32:0]
                
                # Start division
                div_bundle.op1_i.next = op1_val
                div_bundle.op2_i.next = op2_val
                div_bundle.ce_i.next = True
                yield clk.posedge
                div_bundle.ce_i.next = False
                
                # Wait for result (max 37 cycles for remainder, 36 for quotient)
                timeout = 0
                while not div_bundle.ce_o and timeout < 50:
                    yield clk.posedge
                    timeout += 1
                
                if timeout >= 50:
                    print(f"  TIMEOUT: {dividend} / {divisor}")
                    failed += 1
                    continue
                
                # Check result
                expected = exp_r if test_remainder else exp_q
                actual = div_bundle.result_o
                if signed_mode:
                    def to_python_signed(val):
                        """Convert 32-bit two's complement to Python int"""
                        v = int(val)
                        if v & 0x80000000:
                            return v - 0x100000000
                        return v
                    
                    div_str = f"{to_python_signed(op1_val)} / {to_python_signed(op2_val)}"
                    exp_str = str(to_python_signed(expected))
                    act_str = str(to_python_signed(actual))
                else:
                    div_str = f"{int(op1_val)} / {int(op2_val)}"
                    exp_str = f"0x{int(expected):08X}"
                    act_str = f"0x{int(actual):08X}"
                
                op_name = "%" if test_remainder else "/"
                
                if actual == expected:
                    print(f"  ✓ {div_str} {op_name} = {act_str}")
                    passed += 1
                else:
                    print(f"  ✗ {div_str} {op_name} = {act_str} (expected {exp_str})")
                    failed += 1
                    assert False, f"Division mismatch: got {act_str}, expected {exp_str}"
                
                # Wait a few cycles before next test
                for _ in range(3):
                    yield clk.posedge
            
            print(f"\n{'-'*60}")
            print(f"Results: {passed} passed, {failed} failed")
            print(f"{'='*60}\n")
            
            if failed > 0:
                raise AssertionError(f"{failed} test(s) failed")
            
            raise StopSimulation
        
        return instances()
    
    return testbench


# Pytest test cases

def test_divider_unsigned_quotient(sim_env):
    """Test unsigned division (quotient)"""
    tb = divider_testbench(signed_mode=False, test_remainder=False)
    run_sim(tb(), trace=True, waveforms_dir=sim_env["waveforms_dir"], duration=20000, filename="divider_unsigned_quot")


def test_divider_unsigned_remainder(sim_env):
    """Test unsigned modulo (remainder)"""
    tb = divider_testbench(signed_mode=False, test_remainder=True)
    run_sim(tb(), trace=True, waveforms_dir=sim_env["waveforms_dir"], duration=50000, filename="divider_unsigned_rem")


def test_divider_signed_quotient(sim_env):
    """Test signed division (quotient)"""
    tb = divider_testbench(signed_mode=True, test_remainder=False)
    run_sim(tb(), trace=True, waveforms_dir=sim_env["waveforms_dir"], duration=50000, filename="divider_signed_quot")


def test_divider_signed_remainder(sim_env):
    """Test signed modulo (remainder)"""
    tb = divider_testbench(signed_mode=True, test_remainder=True)
    run_sim(tb(), trace=True, waveforms_dir=sim_env["waveforms_dir"], duration=50000, filename="divider_signed_rem")

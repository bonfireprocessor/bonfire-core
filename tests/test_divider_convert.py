"""
Test VHDL conversion of divider module
"""

import os
from pathlib import Path
from myhdl import *

from rtl.divider import DividerBundle


def test_divider_vhdl_conversion():
    """Test that divider converts to VHDL without errors"""
    
    # Create external interface signals
    clk = Signal(bool(0))
    rst = ResetSignal(0, active=1, isasync=False)
    ce_i = Signal(bool(0))
    op1_i = Signal(intbv(0)[32:])
    op2_i = Signal(intbv(0)[32:])
    signed_i = Signal(bool(0))
    rem_i = Signal(bool(0))
    ce_o = Signal(bool(0))
    result_o = Signal(intbv(0)[32:])
    
    # Create wrapper block that connects external signals to bundle
    @block
    def divider_wrapper(clk, rst, ce_i, op1_i, op2_i, signed_i, rem_i, ce_o, result_o):
        """Wrapper for divider that connects external signals to bundle"""
        
        # Instantiate divider bundle
        divider_bundle = DividerBundle(xlen=32)
        
        # Connect bundle to external signals
        @always_comb
        def connect_inputs():
            divider_bundle.ce_i.next = ce_i
            divider_bundle.op1_i.next = op1_i
            divider_bundle.op2_i.next = op2_i
            divider_bundle.signed_i.next = signed_i
            divider_bundle.rem_i.next = rem_i
        
        @always_comb
        def connect_outputs():
            ce_o.next = divider_bundle.ce_o
            result_o.next = divider_bundle.result_o
        
        # Instantiate divider
        div_inst = divider_bundle.divider(clk, rst)
        
        return instances()
    
    # Instantiate wrapper
    inst = divider_wrapper(clk, rst, ce_i, op1_i, op2_i, signed_i, rem_i, ce_o, result_o)
    
    # Convert to VHDL in project-local vhdl_gen directory
    output_dir = Path(__file__).parent.parent / "vhdl_gen"
    output_dir.mkdir(exist_ok=True)
    
    vhdl_file = output_dir / "divider.vhd"
    
    # Perform conversion
    inst.convert(hdl='VHDL', path=str(output_dir), name="divider")
    
    # Verify VHDL file was created
    assert vhdl_file.exists(), f"VHDL file not created: {vhdl_file}"
    
    # Verify file is not empty
    file_size = vhdl_file.stat().st_size
    assert file_size > 0, f"VHDL file is empty: {vhdl_file}"
    
    # Verify file contains VHDL keywords
    content = vhdl_file.read_text()
    assert "entity" in content.lower(), "VHDL file missing 'entity' keyword"
    assert "architecture" in content.lower(), "VHDL file missing 'architecture' keyword"
    
    print(f"✓ VHDL conversion successful: {vhdl_file} ({file_size} bytes)")

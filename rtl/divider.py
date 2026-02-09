"""
Divider
Part of the bonfire-core CPU (ported from LXP32 CPU)

Original Copyright (c) 2016 by Alex I. Kuznetsov
MyHDL port for bonfire-core

Based on the NRD (Non Restoring Division) algorithm. Takes
36 cycles to calculate quotient (37 for remainder).
"""

from myhdl import *
from rtl import config

def_config = config.BonfireConfig()


class DividerBundle:
    """
    Divider Interface Bundle
    
    Contains all signals for the divider interface plus the @block methods.
    Similar to AluBundle pattern used in bonfire-core.
    """
    
    def __init__(self, xlen=32):
        # Inputs
        self.op1_i = Signal(modbv(0)[xlen:])  # Dividend
        self.op2_i = Signal(modbv(0)[xlen:])  # Divisor
        self.signed_i = Signal(bool(0))       # 1=signed division, 0=unsigned
        self.rem_i = Signal(bool(0))          # 1=compute remainder, 0=compute quotient
        self.ce_i = Signal(bool(0))           # Chip enable / start division
        
        # Outputs
        self.result_o = Signal(modbv(0)[xlen:])  # Result (quotient or remainder)
        self.ce_o = Signal(bool(0))              # Output enable (result ready)
        
        # Constants
        self.xlen = xlen
    
    @block
    def Complementor(self, clk_i, compl_i, d_i, d_o):
        """
        Complementor - Computes a 2's complement of its input
        
        Used as an auxiliary unit in the divider.
        
        clk_i: Signal - Clock
        compl_i: Signal - Complement control (1=complement, 0=pass through)
        d_i: Signal(intbv[32]) - Data input
        d_o: Signal(intbv[32]) - Data output
        """
        
        # Internal signals
        d_prepared = Signal(modbv(0)[32:0])  # 32 bits
        sum_low = Signal(modbv(0)[17:0])  # 17 bits (16 bits + carry)
        d_high = Signal(modbv(0)[16:0])  # 16 bits
        sum_high = Signal(modbv(0)[16:0])  # 16 bits
        
        @always_comb
        def prepare():
            """XOR input with complement control bit"""
            temp = modbv(0)[32:0]  # 32 bits
            for i in range(32):
                temp[i] = bool(d_i[i]) ^ bool(compl_i)
            d_prepared.next = temp
        
        @always(clk_i.posedge)
        def compute():
            """Pipelined 2's complement computation (split into low/high)"""
            # Low 16 bits + carry
            sum_low.next = d_prepared[16:0] + compl_i
            # High 16 bits - avoid [32:16] slice, use shift instead
            d_high.next = d_prepared >> 16
        
        @always_comb
        def output():
            """Combine high and low parts"""
            sum_high.next = d_high + sum_low[16]
            d_o.next = concat(sum_high, sum_low[16:0])
        
        return instances()
    
    @block
    def divider(self, clk_i, rst_i):
        """
        Divider using Non-Restoring Division (NRD) algorithm
        
        Takes 36 cycles for quotient, 37 cycles for remainder.
        Uses interface signals from DividerBundle (self.op1_i, self.op2_i, etc.)
        
        clk_i: Signal - Clock
        rst_i: ResetSignal - Reset (active high)
        """
        
        # Complementor signals
        compl_inv = Signal(bool(0))
        compl_mux = Signal(intbv(0)[32:0])
        compl_out = Signal(intbv(0)[32:0])
        
        inv_res = Signal(bool(0))
        
        # Divider FSM signals
        fsm_ce = Signal(bool(0))
        
        dividend = Signal(modbv(0)[32:0])  # 32 bits
        divisor = Signal(modbv(0)[33:0])  # 33 bits for sign extension
        want_remainder = Signal(bool(0))
        
        partial_remainder = Signal(modbv(0)[33:0])  # 33 bits
        addend = Signal(modbv(0)[33:0])  # 33 bits
        sum_val = Signal(modbv(0)[33:0])  # 33 bits (VHDL wraps on overflow)
        sum_positive = Signal(bool(0))
        sum_subtract = Signal(bool(0))
        
        cnt = Signal(intbv(0, min=0, max=35))
        
        ceo = Signal(bool(0))
        
        # Output restoration signals
        remainder_corrector = Signal(modbv(0)[32:0])  # 32 bits
        remainder_corrector_1 = Signal(bool(0))
        remainder_pos = Signal(modbv(0)[32:0])  # 32 bits
        result_pos = Signal(modbv(0)[32:0])  # 32 bits
        op2_zero = Signal(bool(0))
        
        # Instantiate complementor
        compl_inst = self.Complementor(clk_i, compl_inv, compl_mux, compl_out)
        
        @always_comb
        def compl_mux_logic():
            """Select complementor input"""
            if self.ce_i:
                compl_inv.next = bool(self.op1_i[31]) and bool(self.signed_i)
                compl_mux.next = self.op1_i
            else:
                compl_inv.next = inv_res
                compl_mux.next = result_pos
        
        @always_comb
        def zero_detect():
            """Detect division by zero"""
            op2_zero.next = (self.op2_i == 0)
        
        @always_seq(clk_i.posedge, reset=rst_i)
        def fsm_control():
            """Control FSM and result inversion"""
            fsm_ce.next = self.ce_i
            
            if self.ce_i:
                want_remainder.next = self.rem_i
                
                if self.rem_i:
                    # Remainder: keep sign of dividend
                    inv_res.next = bool(self.op1_i[31]) and bool(self.signed_i)
                else:
                    # Quotient: invert if signs differ (and not div by zero)
                    inv_res.next = bool(self.op1_i[31] ^ self.op2_i[31]) and bool(self.signed_i) and not bool(op2_zero)
        
        @always_comb
        def adder_input():
            """Generate addend for main adder (XOR with sum_subtract)"""
            temp = modbv(0)[33:0]  # 33 bits
            for i in range(33):
                temp[i] = bool(divisor[i]) ^ bool(sum_subtract)
            addend.next = temp
        
        @always_comb
        def adder():
            """Main adder/subtractor"""
            sum_val.next = partial_remainder + addend + sum_subtract
            # VHDL: sum_positive<=not sum(32);  -- sum is 33 bits (32 downto 0)
            # sum_val is 34 bits to hold overflow, but we check bit 32 (MSB of 33-bit portion)
            sum_positive.next = not bool(sum_val[32])
        
        @always_seq(clk_i.posedge, reset=rst_i)
        def divider_fsm():
            """Main divider state machine"""
            # Generate output enable pulse
            if cnt == 1:
                ceo.next = True
            else:
                ceo.next = False
            
            if self.ce_i:
                # Load divisor with sign extension
                divisor.next[32:0] = self.op2_i
                divisor.next[32] = bool(self.op2_i[31]) and bool(self.signed_i)
            
            if fsm_ce:
                # Initialize division
                # Shift dividend left by 1, store in dividend register
                # VHDL: dividend<=unsigned(compl_out(30 downto 0)&"0");
                # compl_out(30 downto 0) = MyHDL [31:0] = bits 0-30 (31 bits)
                dividend.next = concat(compl_out[31:0], False)
                # Partial remainder gets MSB of complemented dividend
                # VHDL: partial_remainder<=to_unsigned(0,32)&compl_out(31);
                partial_remainder.next = concat(modbv(0)[32:0], compl_out[31])
                sum_subtract.next = not bool(divisor[32])
                
                if want_remainder:
                    cnt.next = 34
                else:
                    cnt.next = 33
            else:
                # Division iteration
                # VHDL: partial_remainder<=sum(31 downto 0)&dividend(31);
                # sum(31 downto 0) = MyHDL sum_val[32:0] = bits 0-31 (32 bits)
                partial_remainder.next = concat(sum_val[32:0], dividend[31])
                sum_subtract.next = bool(sum_positive) ^ bool(divisor[32])
                # VHDL: dividend<=dividend(30 downto 0)&sum_positive;
                # dividend(30 downto 0) = MyHDL [31:0] = bits 0-30 (31 bits)
                dividend.next = concat(dividend[31:0], sum_positive)
                
                if cnt > 0:
                    cnt.next = cnt - 1
        
        @always(clk_i.posedge)
        def output_restoration():
            """Output restoration circuit for final remainder correction"""
            # Compute remainder corrector
            temp = modbv(0)[32:0]  # 32 bits
            for i in range(32):
                temp[i] = bool( divisor[i] ^ divisor[32]) and not sum_positive
            remainder_corrector.next = temp
            
            remainder_corrector_1.next = divisor[32] and not sum_positive
            
            # Restore positive remainder
            # VHDL: partial_remainder(32 downto 1) = bits 32-1 = shift right by 1
            remainder_pos.next = (partial_remainder >> 1) + remainder_corrector + remainder_corrector_1
        
        @always_comb
        def result_select():
            """Select between remainder and quotient"""
            if want_remainder:
                result_pos.next = remainder_pos
            else:
                result_pos.next = dividend
        
        @always_comb
        def outputs():
            """Assign module outputs"""
            self.result_o.next = compl_out
            self.ce_o.next = ceo
        
        return instances()


class DividerUnit:
    """
    Compatibility wrapper for old DividerUnit interface
    
    Implements Non-Restoring Division (NRD) algorithm
    - 36 cycles for quotient
    - 37 cycles for remainder
    - Supports signed and unsigned division
    
    This class exists for backwards compatibility with existing testbenches.
    New code should use DividerBundle directly.
    """
    
    def __init__(self, config=def_config):
        self.config = config
        self.xlen = config.xlen
    
    @block
    def Complementor(self, clk_i, compl_i, d_i, d_o):
        """Wrapper for DividerBundle.Complementor"""
        bundle = DividerBundle(self.xlen)
        return bundle.Complementor(clk_i, compl_i, d_i, d_o)
    
    @block
    def Divider(self, clk_i, rst_i, ce_i, op1_i, op2_i, signed_i, rem_i, ce_o, result_o):
        """
        Wrapper for DividerBundle.divider with old interface
        
        Maps external signals to bundle and instantiates divider block.
        """
        # Create bundle
        bundle = DividerBundle(self.xlen)
        
        # Connect bundle inputs to external signals
        @always_comb
        def connect_inputs():
            bundle.ce_i.next = ce_i
            bundle.op1_i.next = op1_i
            bundle.op2_i.next = op2_i
            bundle.signed_i.next = signed_i
            bundle.rem_i.next = rem_i
        
        # Connect bundle outputs to external signals
        @always_comb
        def connect_outputs():
            ce_o.next = bundle.ce_o
            result_o.next = bundle.result_o
        
        # Instantiate divider
        div_inst = bundle.divider(clk_i, rst_i)
        
        return instances()

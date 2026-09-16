# Copyright (c) 2026 The Bonfire Project
# License: See LICENSE

"""Four-stage RV32 multiplier built from 16 x 16 partial products."""

from __future__ import annotations

from myhdl import (
    Signal,
    always,
    always_comb,
    always_seq,
    block,
    concat,
    instances,
    modbv,
)


class MultiplierBundle:
    """Pipelined multiplier interface.

    ``signed_a_i`` and ``signed_b_i`` independently control operand
    interpretation.  ``high_i`` selects bits 63:32 instead of bits 31:0.
    Together these controls cover MUL, MULH, MULHSU and MULHU.

    The implementation has four registered stages and accepts one request per
    clock.  A result is marked valid at the fourth active clock edge, counting
    the edge which accepts ``ce_i`` as the first stage.
    """

    def __init__(self, xlen: int = 32) -> None:
        assert xlen == 32, "The cascaded multiplier currently supports RV32 only"

        self.op1_i = Signal(modbv(0)[xlen:])
        self.op2_i = Signal(modbv(0)[xlen:])
        self.signed_a_i = Signal(bool(0))
        self.signed_b_i = Signal(bool(0))
        self.high_i = Signal(bool(0))
        self.ce_i = Signal(bool(0))
        self.cancel_i = Signal(bool(0))

        self.result_o = Signal(modbv(0)[xlen:])
        self.ce_o = Signal(bool(0))

        self.xlen = xlen

    @block
    def multiplier(self, clock, reset):
        """Instantiate the four-stage 16 x 16 cascaded multiplier."""

        mask32 = 0xFFFFFFFF
        mask64 = 0xFFFFFFFFFFFFFFFF

        # Stage 1: normalize independently signed operands to magnitudes.
        magnitude_a_s1 = Signal(modbv(0)[32:])
        magnitude_b_s1 = Signal(modbv(0)[32:])
        negative_s1 = Signal(bool(0))
        high_s1 = Signal(bool(0))

        # Stage 2: four unsigned 16 x 16 products.  FPGA tools can map each
        # multiplication directly to a native 18 x 18 multiplier block.
        product_ll_s2 = Signal(modbv(0)[32:])
        product_lh_s2 = Signal(modbv(0)[32:])
        product_hl_s2 = Signal(modbv(0)[32:])
        product_hh_s2 = Signal(modbv(0)[32:])
        negative_s2 = Signal(bool(0))
        high_s2 = Signal(bool(0))

        # Stage 3: cascade the four partial products into the unsigned result.
        unsigned_product_s3 = Signal(modbv(0)[64:])
        negative_s3 = Signal(bool(0))
        high_s3 = Signal(bool(0))

        # Stage 4: apply the final sign and select the architectural half.
        result_s4 = Signal(modbv(0)[32:])

        valid_s1 = Signal(bool(0))
        valid_s2 = Signal(bool(0))
        valid_s3 = Signal(bool(0))
        valid_s4 = Signal(bool(0))

        @always(clock.posedge)
        def data_pipeline():
            sign_a = bool(self.signed_a_i and self.op1_i[31])
            sign_b = bool(self.signed_b_i and self.op2_i[31])

            if sign_a:
                magnitude_a_s1.next = ((~self.op1_i) + 1) & mask32
            else:
                magnitude_a_s1.next = self.op1_i

            if sign_b:
                magnitude_b_s1.next = ((~self.op2_i) + 1) & mask32
            else:
                magnitude_b_s1.next = self.op2_i

            negative_s1.next = sign_a != sign_b
            high_s1.next = self.high_i

            product_ll_s2.next = \
                magnitude_a_s1[16:0] * magnitude_b_s1[16:0]
            product_lh_s2.next = \
                magnitude_a_s1[16:0] * magnitude_b_s1[32:16]
            product_hl_s2.next = \
                magnitude_a_s1[32:16] * magnitude_b_s1[16:0]
            product_hh_s2.next = \
                magnitude_a_s1[32:16] * magnitude_b_s1[32:16]
            negative_s2.next = negative_s1
            high_s2.next = high_s1

            # Assemble the 64-bit value as four radix-2**16 limbs.  Explicit
            # limb carries keep conversion widths unambiguous and form the
            # intended short cascade between the native multiplier blocks.
            sum_limb1 = modbv(0)[18:]
            sum_limb2 = modbv(0)[18:]
            sum_limb3 = modbv(0)[17:]
            sum_limb1[:] = product_ll_s2[32:16] + \
                product_lh_s2[16:0] + product_hl_s2[16:0]
            sum_limb2[:] = product_lh_s2[32:16] + \
                product_hl_s2[32:16] + product_hh_s2[16:0] + \
                sum_limb1[18:16]
            sum_limb3[:] = product_hh_s2[32:16] + sum_limb2[18:16]
            unsigned_product_s3.next = concat(
                sum_limb3[16:0],
                sum_limb2[16:0],
                sum_limb1[16:0],
                product_ll_s2[16:0],
            )
            negative_s3.next = negative_s2
            high_s3.next = high_s2

            corrected_product = modbv(0)[64:]
            if negative_s3:
                corrected_product[:] = \
                    ((~unsigned_product_s3) + 1) & mask64
            else:
                corrected_product[:] = unsigned_product_s3

            if high_s3:
                result_s4.next = corrected_product >> 32
            else:
                result_s4.next = corrected_product & mask32

        @always_seq(clock.posedge, reset=reset)
        def valid_pipeline():
            if self.cancel_i:
                valid_s1.next = False
                valid_s2.next = False
                valid_s3.next = False
                valid_s4.next = False
            else:
                valid_s1.next = self.ce_i
                valid_s2.next = valid_s1
                valid_s3.next = valid_s2
                valid_s4.next = valid_s3

        @always_comb
        def outputs():
            self.result_o.next = result_s4
            self.ce_o.next = valid_s4

        return instances()

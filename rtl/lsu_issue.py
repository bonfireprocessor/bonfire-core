"""
Local Load/Store Issue Validation Shared by Execute and the LSU
(c) 2026 The Bonfire Project
License: See LICENSE

Local load/store issue validation shared by Execute and the LSU.
"""

from myhdl import Signal, always_comb, block, instances, modbv

from rtl.instructions import LoadFunct3
from rtl.static_data_access import (
    DataAccessFaultMode,
    StaticDataAccessCheckerBundle,
)


class LoadStoreIssueBundle:
    """Combinational address, format, alignment and access-policy results."""

    def __init__(self, config):
        xlen = config.xlen
        self.config = config
        self.effective_address_o = Signal(modbv(0)[xlen:])
        self.byte_mode_o = Signal(bool(0))
        self.hword_mode_o = Signal(bool(0))
        self.word_mode_o = Signal(bool(0))
        self.unsigned_o = Signal(bool(0))
        self.invalid_o = Signal(bool(0))
        self.misaligned_o = Signal(bool(0))
        self.access_fault_o = Signal(bool(0))

    @block
    def checker(self, access_i, store_i, funct3_i, op1_i, displacement_i):
        xlen = self.config.xlen
        static_access_map = \
            self.config.data_access_fault_mode == DataAccessFaultMode.STATIC_MAP
        if static_access_map:
            access_checker = StaticDataAccessCheckerBundle(xlen)
            access_checker_inst = access_checker.checker(
                self.config.data_access_regions)

            @always_comb
            def static_access_connect():
                access_checker.address_i.next = self.effective_address_o
                access_checker.load_i.next = access_i and not store_i
                access_checker.store_i.next = access_i and store_i
                self.access_fault_o.next = access_checker.fault_o
        else:
            @always_comb
            def static_access_connect():
                # Keep a real input dependency here: MyHDL rejects an
                # always_comb process with an empty sensitivity list.
                self.access_fault_o.next = access_i and not access_i

        @always_comb
        def check():
            funct = funct3_i
            effective_address = modbv(0)[xlen:]
            byte_mode = funct[2:0] == LoadFunct3.RV32_F3_LB
            hword_mode = funct[2:0] == LoadFunct3.RV32_F3_LH
            word_mode = funct[2:0] == LoadFunct3.RV32_F3_LW

            effective_address[:] = op1_i + displacement_i.signed()
            self.effective_address_o.next = effective_address
            self.byte_mode_o.next = byte_mode
            self.hword_mode_o.next = hword_mode
            self.word_mode_o.next = word_mode
            self.unsigned_o.next = funct[2]
            self.invalid_o.next = \
                (funct[2] and store_i) or not (
                    byte_mode or hword_mode or word_mode)
            self.misaligned_o.next = \
                (hword_mode and effective_address[0]) or \
                (word_mode and effective_address[2:0] != 0)

        return instances()

"""Elaboration-time static data-access policy and its RTL checker."""

from myhdl import Signal, always_comb, block, instances, modbv


class DataAccessFaultMode:
    """How a concrete implementation determines LSU access faults."""

    BUS_RESPONSE = "bus_response"
    STATIC_MAP = "static_map"


class DataAccessRegion:
    """One statically decoded, permission-controlled data address region."""

    def __init__(self, base, address_mask, readable=True, writable=True):
        self.base = int(base)
        self.address_mask = int(address_mask)
        self.readable = bool(readable)
        self.writable = bool(writable)

    @classmethod
    def from_adrmask(cls, adrmask, xlen=32, readable=True, writable=True):
        return cls(
            adrmask.base_address(xlen), adrmask.address_mask(xlen),
            readable=readable, writable=writable)

    def selector(self, xlen):
        """Return the contiguous high-bit selector shared with ``AdrMask``."""
        full_mask = (1 << xlen) - 1
        address_mask = self.address_mask & full_mask
        if address_mask == 0:
            raise ValueError("static data-access region needs a non-empty mask")
        lower = 0
        while not (address_mask & (1 << lower)):
            lower += 1
        expected_mask = full_mask ^ ((1 << lower) - 1)
        if address_mask != expected_mask:
            raise ValueError(
                "static data-access region mask must select contiguous high bits")
        width = xlen - lower
        if width > 31:
            raise ValueError(
                "static data-access region selector exceeds VHDL integer width")
        return lower, self.base >> lower


class StaticDataAccessCheckerBundle:
    """RTL interface for an elaboration-time static LSU address map."""

    def __init__(self, xlen):
        self.address_i = Signal(modbv(0)[xlen:])
        self.load_i = Signal(bool(0))
        self.store_i = Signal(bool(0))
        self.fault_o = Signal(bool(0))
        self.xlen = xlen

    @block
    def checker(self, regions):
        """Assert ``fault_o`` for an active access outside its permissions."""
        xlen = self.xlen
        regions = tuple(regions)
        assert len(regions) <= 8, \
            "static data-access checker supports at most eight regions"
        region_count = len(regions)
        # Padding supplies valid selector metadata only. Inactive slots never
        # take part in matching, so it creates neither an alias nor hardware.
        regions += tuple(
            DataAccessRegion(0, 1 << (xlen - 1), readable=False,
                             writable=False)
            for _ in range(8 - region_count))

        region0_lower, region0_value = regions[0].selector(xlen)
        region0_readable, region0_writable = regions[0].readable, regions[0].writable
        region1_lower, region1_value = regions[1].selector(xlen)
        region1_readable, region1_writable = regions[1].readable, regions[1].writable
        region2_lower, region2_value = regions[2].selector(xlen)
        region2_readable, region2_writable = regions[2].readable, regions[2].writable
        region3_lower, region3_value = regions[3].selector(xlen)
        region3_readable, region3_writable = regions[3].readable, regions[3].writable
        region4_lower, region4_value = regions[4].selector(xlen)
        region4_readable, region4_writable = regions[4].readable, regions[4].writable
        region5_lower, region5_value = regions[5].selector(xlen)
        region5_readable, region5_writable = regions[5].readable, regions[5].writable
        region6_lower, region6_value = regions[6].selector(xlen)
        region6_readable, region6_writable = regions[6].readable, regions[6].writable
        region7_lower, region7_value = regions[7].selector(xlen)
        region7_readable, region7_writable = regions[7].readable, regions[7].writable

        @always_comb
        def check_access():
            match0 = False
            match1 = False
            match2 = False
            match3 = False
            match4 = False
            match5 = False
            match6 = False
            match7 = False
            if region_count > 0:
                match0 = self.address_i[xlen:region0_lower] == region0_value
            if region_count > 1:
                match1 = self.address_i[xlen:region1_lower] == region1_value
            if region_count > 2:
                match2 = self.address_i[xlen:region2_lower] == region2_value
            if region_count > 3:
                match3 = self.address_i[xlen:region3_lower] == region3_value
            if region_count > 4:
                match4 = self.address_i[xlen:region4_lower] == region4_value
            if region_count > 5:
                match5 = self.address_i[xlen:region5_lower] == region5_value
            if region_count > 6:
                match6 = self.address_i[xlen:region6_lower] == region6_value
            if region_count > 7:
                match7 = self.address_i[xlen:region7_lower] == region7_value

            allowed = False
            if self.store_i:
                allowed = \
                    (match0 and region0_writable) or \
                    (match1 and region1_writable) or \
                    (match2 and region2_writable) or \
                    (match3 and region3_writable) or \
                    (match4 and region4_writable) or \
                    (match5 and region5_writable) or \
                    (match6 and region6_writable) or \
                    (match7 and region7_writable)
            else:
                allowed = \
                    (match0 and region0_readable) or \
                    (match1 and region1_readable) or \
                    (match2 and region2_readable) or \
                    (match3 and region3_readable) or \
                    (match4 and region4_readable) or \
                    (match5 and region5_readable) or \
                    (match6 and region6_readable) or \
                    (match7 and region7_readable)

            self.fault_o.next = (self.load_i or self.store_i) and not allowed

        return instances()

from myhdl import Simulation, StopSimulation, delay, instance

from rtl.static_data_access import (
    DataAccessRegion,
    StaticDataAccessCheckerBundle,
)


def test_static_data_access_checker_permissions_and_boundaries():
    checker = StaticDataAccessCheckerBundle(32)
    dut = checker.checker((
        DataAccessRegion(0x80010000, 0xffff0000, readable=True,
                         writable=False),
        DataAccessRegion(0x80020000, 0xffff0000, readable=False,
                         writable=True),
    ))

    @instance
    def stimulus():
        checker.address_i.next = 0x80010000
        checker.load_i.next = True
        checker.store_i.next = False
        yield delay(1)
        assert not checker.fault_o

        checker.address_i.next = 0x8001ffff
        yield delay(1)
        assert not checker.fault_o

        checker.store_i.next = True
        checker.load_i.next = False
        yield delay(1)
        assert checker.fault_o

        checker.address_i.next = 0x80020000
        yield delay(1)
        assert not checker.fault_o

        checker.store_i.next = False
        checker.load_i.next = True
        yield delay(1)
        assert checker.fault_o

        checker.address_i.next = 0x80030000
        yield delay(1)
        assert checker.fault_o

        checker.load_i.next = False
        yield delay(1)
        assert not checker.fault_o
        raise StopSimulation

    Simulation(dut, stimulus).run()

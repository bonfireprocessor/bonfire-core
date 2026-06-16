"""
Bonfire interconnect for dbus_bundle
(c) 2019,2020 The Bonfire Project
License: See LICENSE
"""

from __future__ import annotations, print_function

from typing import Any, Sequence

from myhdl import *

from rtl.bonfire_interfaces import DbusBundle
from rtl.type_aliases import BitSignal
from util.diagnostics import get_diagnostics

class AdrMask:
    def __init__(self, upper: int, lower: int, value: int) -> None:
        self.upper: int = upper
        self.lower: int = lower
        self.mask: int = value

    def base_address(self, xlen: int = 32) -> int:
        return self.mask << self.lower

    def address_mask(self, xlen: int = 32) -> int:
        width = self.upper - self.lower
        field_mask = ((1 << width) - 1) << self.lower
        return field_mask & ((1 << xlen) - 1)

    def mapped_range(self, xlen: int = 32) -> tuple[int, int]:
        address_mask = self.address_mask(xlen)
        base = self.base_address(xlen)
        full_mask = (1 << xlen) - 1
        return base, base | (full_mask ^ address_mask)



class DbusInterConnects:

    @staticmethod
    def _validate_adrmask(adrmask: AdrMask, xlen: int, label: str) -> None:
        assert 0 <= adrmask.lower < adrmask.upper <= xlen, (
            "{} invalid address mask bit range: upper={} lower={} xlen={}".format(
                label, adrmask.upper, adrmask.lower, xlen))
        width = adrmask.upper - adrmask.lower
        assert 0 <= adrmask.mask < (1 << width), (
            "{} invalid address mask value: mask=0x{:x} does not fit in {} bits".format(
                label, adrmask.mask, width))

    @staticmethod
    def _adrmasks_overlap(a: AdrMask, b: AdrMask, xlen: int) -> bool:
        common_lower = min(a.lower, b.lower)
        common_upper = max(a.upper, b.upper)
        width = common_upper - common_lower
        a_value = (a.base_address(xlen) >> common_lower) & ((1 << width) - 1)
        b_value = (b.base_address(xlen) >> common_lower) & ((1 << width) - 1)
        a_mask = a.address_mask(xlen) >> common_lower
        b_mask = b.address_mask(xlen) >> common_lower
        return (a_value & b_mask) == (b_value & a_mask)

    @staticmethod
    def _validate_and_log_mapping(slaves: Sequence[DbusBundle],
                                  adrmasks: Sequence[AdrMask],
                                  names: Sequence[str],
                                  xlen: int,
                                  interconnect_name: str) -> None:
        active: list[tuple[int, DbusBundle, AdrMask, str]] = []
        assert len(slaves) == len(adrmasks)
        assert len(slaves) == len(names)

        diagnostics = get_diagnostics()
        diagnostics.detail("{}: DBUS address map".format(interconnect_name))
        for i, slave in enumerate(slaves):
            if slave is None:
                assert adrmasks[i] is None, (
                    "{} slot {} {} is disabled but has an address mask".format(
                        interconnect_name, i, names[i]))
                diagnostics.detail("{}:   slot {} {} disabled".format(interconnect_name, i, names[i]))
                continue

            adrmask = adrmasks[i]
            assert adrmask is not None, (
                "{} slot {} {} has a slave but no address mask".format(
                    interconnect_name, i, names[i]))
            DbusInterConnects._validate_adrmask(
                adrmask, xlen, "{} slot {} {}".format(interconnect_name, i, names[i]))
            base, end = adrmask.mapped_range(xlen)
            address_mask = adrmask.address_mask(xlen)
            diagnostics.detail(
                "{}:   slot {} {} active: bits [{}:{}] == 0x{:x}, "
                "base=0x{:08x}, addr_mask=0x{:08x}, range=0x{:08x}..0x{:08x}".format(
                    interconnect_name, i, names[i], adrmask.upper - 1, adrmask.lower,
                    adrmask.mask, base, address_mask, base, end))
            active.append((i, slave, adrmask, names[i]))

        for a_index, _, a_mask, a_name in active:
            for b_index, _, b_mask, b_name in active:
                if b_index <= a_index:
                    continue
                assert not DbusInterConnects._adrmasks_overlap(a_mask, b_mask, xlen), (
                    "{} slots {} {} and {} {} have overlapping address decode".format(
                        interconnect_name, a_index, a_name, b_index, b_name))

    @staticmethod
    @block
    def MasterNSlaveSignals(master_en_o: BitSignal, master_adr_o: Any, master_we_o: Any,
                            master_db_wr: Any, master_ack_i: BitSignal,
                            master_error_i: BitSignal, master_stall_i: BitSignal,
                            master_db_rd: Any, slave_port_en_o: Sequence[Any],
                            slave_port_adr_o: Sequence[Any], slave_port_we_o: Sequence[Any],
                            slave_port_db_wr: Sequence[Any], slave_port_ack_i: Sequence[Any],
                            slave_port_error_i: Sequence[Any], slave_port_stall_i: Sequence[Any],
                            slave_port_db_rd: Sequence[Any], clock: BitSignal,
                            reset: BitSignal, adrmasks: Sequence[AdrMask]) -> Any:
        slave_count = len(slave_port_en_o)
        assert slave_count == len(adrmasks), "slave signals and adrmasks must have the same length"
        assert slave_count == len(slave_port_adr_o)
        assert slave_count == len(slave_port_we_o)
        assert slave_count == len(slave_port_db_wr)
        assert slave_count == len(slave_port_ack_i)
        assert slave_count == len(slave_port_error_i)
        assert slave_count == len(slave_port_stall_i)
        assert slave_count == len(slave_port_db_rd)
        assert slave_count > 0, "at least one slave is required"

        s_en = Signal(modbv(0)[slave_count:])
        s_en_r = Signal(modbv(0)[slave_count:])
        mux_sel = Signal(modbv(0)[slave_count:])
        s_en_decoded = [Signal(bool(0)) for _ in range(slave_count)]
        mux_slave_ack = [Signal(bool(0)) for _ in range(slave_count)]
        mux_slave_error = [Signal(bool(0)) for _ in range(slave_count)]
        mux_slave_stall = [Signal(bool(0)) for _ in range(slave_count)]
        mux_slave_db_rd = [Signal(modbv(0)[len(master_db_rd):]) for _ in range(slave_count)]

        busy: BitSignal = Signal(bool(0))
        ack: BitSignal = Signal(bool(0))

        @always_seq(clock.posedge, reset=reset)
        def seq():
            if busy and ack:
                busy.next = False
            else:
                s_en_r.next = s_en
                b = False
                for i in range(slave_count):
                    b = b or s_en[i]

                busy.next = b and not ack

        @always_comb
        def mux_sel_proc():
            for i in range(slave_count):
                mux_sel.next[i] = s_en[i] or (s_en_r[i] and busy)

        adrsel_instances = []

        @block
        def make_adrsel(i: int, mask_upper: int, mask_lower: int, mask_value: int) -> Any:
            @always_comb
            def adrsel():
                s_en_decoded[i].next = master_adr_o[mask_upper:mask_lower] == mask_value and master_en_o

            return adrsel

        for i in range(slave_count):
            adrsel_instances.append(make_adrsel(
                i, adrmasks[i].upper, adrmasks[i].lower, adrmasks[i].mask))

        @always_comb
        def adrsel_vector():
            for i in range(slave_count):
                s_en.next[i] = s_en_decoded[i]

        slave_output_instances = []

        @block
        def make_slave_outputs(i: int, en_o: BitSignal, adr_o: Any, db_wr_o: Any, we_o: Any) -> Any:
            @always_comb
            def slave_outputs():
                en_o.next = s_en[i]
                adr_o.next = master_adr_o
                db_wr_o.next = master_db_wr
                we_o.next = master_we_o

            return slave_outputs

        for i in range(slave_count):
            slave_output_instances.append(make_slave_outputs(
                i, slave_port_en_o[i], slave_port_adr_o[i],
                slave_port_db_wr[i], slave_port_we_o[i]))

        slave_input_instances = []

        @block
        def make_slave_inputs(i: int, ack_i: BitSignal, error_i: BitSignal,
                              stall_i: BitSignal, db_rd_i: Any) -> Any:
            @always_comb
            def slave_inputs():
                mux_slave_ack[i].next = ack_i
                mux_slave_error[i].next = error_i
                mux_slave_stall[i].next = stall_i
                mux_slave_db_rd[i].next = db_rd_i

            return slave_inputs

        for i in range(slave_count):
            slave_input_instances.append(make_slave_inputs(
                i, slave_port_ack_i[i], slave_port_error_i[i],
                slave_port_stall_i[i], slave_port_db_rd[i]))

        @always_comb
        def master_inputs():
            stall = busy and master_en_o and s_en != s_en_r
            t_ack = False
            t_error = False
            selected = False
            master_db_rd.next = 0

            for i in range(slave_count):
                if mux_sel[i]:
                    selected = True
                    stall = stall or mux_slave_stall[i]
                    t_ack = mux_slave_ack[i] == True
                    t_error = mux_slave_error[i] == True
                    master_db_rd.next = mux_slave_db_rd[i]

            if not selected:
                t_error = bool(master_en_o)

            master_error_i.next = t_error
            master_ack_i.next = t_ack
            ack.next = t_ack
            master_stall_i.next = stall

        return instances()

    @staticmethod
    @block
    def Master8Slaves(master: DbusBundle, clock: BitSignal, reset: BitSignal,
                      slave0: DbusBundle | None = None,
                      slave1: DbusBundle | None = None,
                      slave2: DbusBundle | None = None,
                      slave3: DbusBundle | None = None,
                      slave4: DbusBundle | None = None,
                      slave5: DbusBundle | None = None,
                      slave6: DbusBundle | None = None,
                      slave7: DbusBundle | None = None,
                      adrmask0: AdrMask | None = None,
                      adrmask1: AdrMask | None = None,
                      adrmask2: AdrMask | None = None,
                      adrmask3: AdrMask | None = None,
                      adrmask4: AdrMask | None = None,
                      adrmask5: AdrMask | None = None,
                      adrmask6: AdrMask | None = None,
                      adrmask7: AdrMask | None = None) -> Any:
        slots = (slave0, slave1, slave2, slave3, slave4, slave5, slave6, slave7)
        masks = (adrmask0, adrmask1, adrmask2, adrmask3, adrmask4, adrmask5, adrmask6, adrmask7)
        names = ("slave0", "slave1", "slave2", "slave3", "slave4", "slave5", "slave6", "slave7")

        DbusInterConnects._validate_and_log_mapping(
            slots, masks, names, master.xlen, "Master8Slaves")

        active_slaves = []
        active_masks = []
        for i, slave in enumerate(slots):
            if slave is not None:
                active_slaves.append(slave)
                active_masks.append(masks[i])

        if active_slaves:
            slave_port_en_o = tuple(slave.en_o for slave in active_slaves)
            slave_port_adr_o = tuple(slave.adr_o for slave in active_slaves)
            slave_port_we_o = tuple(slave.we_o for slave in active_slaves)
            slave_port_db_wr = tuple(slave.db_wr for slave in active_slaves)
            slave_port_ack_i = tuple(slave.ack_i for slave in active_slaves)
            slave_port_error_i = tuple(slave.error_i for slave in active_slaves)
            slave_port_stall_i = tuple(slave.stall_i for slave in active_slaves)
            slave_port_db_rd = tuple(slave.db_rd for slave in active_slaves)

            ic = DbusInterConnects.MasterNSlaveSignals(
                master.en_o, master.adr_o, master.we_o, master.db_wr,
                master.ack_i, master.error_i, master.stall_i, master.db_rd,
                slave_port_en_o, slave_port_adr_o, slave_port_we_o, slave_port_db_wr,
                slave_port_ack_i, slave_port_error_i, slave_port_stall_i, slave_port_db_rd,
                clock, reset, active_masks)
        else:
            @always_comb
            def no_slaves():
                master.ack_i.next = False
                master.error_i.next = master.en_o
                master.stall_i.next = False
                master.db_rd.next = 0

        return instances()

    @staticmethod
    @block
    def Master3Slaves(master: DbusBundle, slave1: DbusBundle,
                                     slave2: DbusBundle, slave3: DbusBundle,
                                     clock: BitSignal, reset: BitSignal,
                                     adrmask1: AdrMask, adrmask2: AdrMask,
                                     adrmask3: AdrMask) -> Any:
        slave_port_en_o = (slave1.en_o, slave2.en_o, slave3.en_o)
        slave_port_adr_o = (slave1.adr_o, slave2.adr_o, slave3.adr_o)
        slave_port_we_o = (slave1.we_o, slave2.we_o, slave3.we_o)
        slave_port_db_wr = (slave1.db_wr, slave2.db_wr, slave3.db_wr)
        slave_port_ack_i = (slave1.ack_i, slave2.ack_i, slave3.ack_i)
        slave_port_error_i = (slave1.error_i, slave2.error_i, slave3.error_i)
        slave_port_stall_i = (slave1.stall_i, slave2.stall_i, slave3.stall_i)
        slave_port_db_rd = (slave1.db_rd, slave2.db_rd, slave3.db_rd)
        adrmasks = (adrmask1, adrmask2, adrmask3)

        ic = DbusInterConnects.MasterNSlaveSignals(
            master.en_o, master.adr_o, master.we_o, master.db_wr,
            master.ack_i, master.error_i, master.stall_i, master.db_rd,
            slave_port_en_o, slave_port_adr_o, slave_port_we_o, slave_port_db_wr,
            slave_port_ack_i, slave_port_error_i, slave_port_stall_i, slave_port_db_rd,
            clock, reset, adrmasks)

        return instances()

    # @staticmethod
    # @block
    # def Master3Slaves(master: DbusBundle, slave1: DbusBundle, slave2: DbusBundle,
    #                   slave3: DbusBundle, clock: BitSignal, reset: BitSignal,
    #                   adrmask1: AdrMask, adrmask2: AdrMask, adrmask3: AdrMask) -> Any:

    #     s_en = Signal(modbv(0)[3:])
    #     s_en_r = Signal(modbv(0)[3:])
    #     mux_sel = Signal(modbv(0)[3:])
       
    #     busy: BitSignal = Signal(bool(0)) # Interconnect busy with an active bus cycle
    #     ack: BitSignal = Signal(bool(0))

    #     @always_seq(clock.posedge,reset=reset)
    #     def seq():

    #         if busy and ack:
    #             busy.next = False
    #         else:
    #             s_en_r.next = s_en
    #             b = False
    #             for i in range(len(s_en)):
    #                 b = b or s_en[i]

    #             busy.next = b and not ack

    #     @always_comb
    #     def mux_sel_proc():
    #         for i in range(len(s_en)):
    #             mux_sel.next[i] = s_en[i] or ( s_en_r[i] and busy ) 

    #     @always_comb
    #     def adrsel():
    #         s_en.next[0] = master.adr_o[adrmask1.upper:adrmask1.lower] == adrmask1.mask and master.en_o 
    #         s_en.next[1] = master.adr_o[adrmask2.upper:adrmask2.lower] == adrmask2.mask and master.en_o 
    #         s_en.next[2] = master.adr_o[adrmask3.upper:adrmask3.lower] == adrmask3.mask and master.en_o 

    #     # @always(clock.posedge)
    #     # def mon():
    #     #     if s_en:
    #     #         print("adr:{} s_en:{}".format(master.adr_o,bin(s_en,3)))    

    #     @always_comb
    #     def comb():
    #         slave1.en_o.next = s_en[0]
    #         slave2.en_o.next = s_en[1]
    #         slave3.en_o.next = s_en[2]
    #         slave1.adr_o.next = master.adr_o
    #         slave2.adr_o.next = master.adr_o
    #         slave3.adr_o.next = master.adr_o
    #         slave1.db_wr.next = master.db_wr
    #         slave2.db_wr.next = master.db_wr
    #         slave3.db_wr.next = master.db_wr
    #         slave1.we_o.next = master.we_o
    #         slave2.we_o.next = master.we_o
    #         slave3.we_o.next = master.we_o

    #         # Stall master when the seleted slave changes.
    #         # This is needed because the interconnet has no mechanism to queue bus cycles
    #         stall = busy and master.en_o and s_en != s_en_r

    #         t_ack = False

    #         master.error_i.next = False 
    #         if mux_sel[0]:
    #             stall = stall or  slave1.stall_i
    #             t_ack = slave1.ack_i.val
    #             master.db_rd.next = slave1.db_rd
    #         elif mux_sel[1]:
    #             stall = stall or slave2.stall_i
    #             t_ack = slave2.ack_i.val
    #             master.db_rd.next = slave2.db_rd
    #             master.error_i.next = False
    #         elif mux_sel[2]:
    #             stall = stall or slave3.stall_i
    #             t_ack = slave3.ack_i.val
    #             master.db_rd.next = slave3.db_rd   
    #         else:
    #             master.error_i.next = master.en_o
    #             master.db_rd.next = 0
                
                
    #         master.ack_i.next = t_ack
    #         ack.next = t_ack                
    #         master.stall_i.next = stall    
            

    #     return instances()

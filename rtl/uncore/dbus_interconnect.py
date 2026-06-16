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

class AdrMask:
    def __init__(self, upper: int, lower: int, value: int) -> None:
        self.upper: int = upper
        self.lower: int = lower
        self.mask: int = value



class DbusInterConnects:

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
    def Master3SlavesViaSignalArrays(master: DbusBundle, slave1: DbusBundle,
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

    @staticmethod
    @block
    def Master3Slaves(master: DbusBundle, slave1: DbusBundle, slave2: DbusBundle,
                      slave3: DbusBundle, clock: BitSignal, reset: BitSignal,
                      adrmask1: AdrMask, adrmask2: AdrMask, adrmask3: AdrMask) -> Any:

        s_en = Signal(modbv(0)[3:])
        s_en_r = Signal(modbv(0)[3:])
        mux_sel = Signal(modbv(0)[3:])
       
        busy: BitSignal = Signal(bool(0)) # Interconnect busy with an active bus cycle
        ack: BitSignal = Signal(bool(0))

        @always_seq(clock.posedge,reset=reset)
        def seq():

            if busy and ack:
                busy.next = False
            else:
                s_en_r.next = s_en
                b = False
                for i in range(len(s_en)):
                    b = b or s_en[i]

                busy.next = b and not ack

        @always_comb
        def mux_sel_proc():
            for i in range(len(s_en)):
                mux_sel.next[i] = s_en[i] or ( s_en_r[i] and busy ) 

        @always_comb
        def adrsel():
            s_en.next[0] = master.adr_o[adrmask1.upper:adrmask1.lower] == adrmask1.mask and master.en_o 
            s_en.next[1] = master.adr_o[adrmask2.upper:adrmask2.lower] == adrmask2.mask and master.en_o 
            s_en.next[2] = master.adr_o[adrmask3.upper:adrmask3.lower] == adrmask3.mask and master.en_o 

        # @always(clock.posedge)
        # def mon():
        #     if s_en:
        #         print("adr:{} s_en:{}".format(master.adr_o,bin(s_en,3)))    

        @always_comb
        def comb():
            slave1.en_o.next = s_en[0]
            slave2.en_o.next = s_en[1]
            slave3.en_o.next = s_en[2]
            slave1.adr_o.next = master.adr_o
            slave2.adr_o.next = master.adr_o
            slave3.adr_o.next = master.adr_o
            slave1.db_wr.next = master.db_wr
            slave2.db_wr.next = master.db_wr
            slave3.db_wr.next = master.db_wr
            slave1.we_o.next = master.we_o
            slave2.we_o.next = master.we_o
            slave3.we_o.next = master.we_o

            # Stall master when the seleted slave changes.
            # This is needed because the interconnet has no mechanism to queue bus cycles
            stall = busy and master.en_o and s_en != s_en_r

            t_ack = False

            master.error_i.next = False 
            if mux_sel[0]:
                stall = stall or  slave1.stall_i
                t_ack = slave1.ack_i.val
                master.db_rd.next = slave1.db_rd
            elif mux_sel[1]:
                stall = stall or slave2.stall_i
                t_ack = slave2.ack_i.val
                master.db_rd.next = slave2.db_rd
                master.error_i.next = False
            elif mux_sel[2]:
                stall = stall or slave3.stall_i
                t_ack = slave3.ack_i.val
                master.db_rd.next = slave3.db_rd   
            else:
                master.error_i.next = master.en_o
                master.db_rd.next = 0
                
                
            master.ack_i.next = t_ack
            ack.next = t_ack                
            master.stall_i.next = stall    
            

        return instances()

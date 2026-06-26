"""
ECP5 JTAGG debug transport testbench.
(c) 2026 The Bonfire Project
License: See LICENSE
"""
from __future__ import annotations

from collections.abc import Generator

from myhdl import ResetSignal, Signal, always_seq, block, instance, instances, modbv, now, StopSimulation

from rtl.config import BonfireConfig
from rtl.debug import DmiBundle, Ecp5JtaggClient, Ecp5JtaggInputBundle, Ecp5JtaggOutputBundle, Ecp5JtaggTapEmulator
from rtl.debug.ecp5_jtagg_client import ECP5_JTAGG_IR_ER1, ECP5_JTAGG_IR_ER2, ECP5_JTAGG_IR_WIDTH
from rtl.debug.ecp5_jtagg_tap import ECP5_JTAG_IDCODE_DEFAULT, ECP5_JTAG_INSTR_BYPASS, ECP5_JTAG_INSTR_IDCODE
from rtl.debug.jtag_dtm import DTM_IDLE, DMI_OP_READ, DMI_OP_WRITE
from tb.ClkDriver import ClkDriver
from tb.debug.tb_jtag_dtm import JtagBFM


@block
def ecp5_jtagg_testbench(verbose: bool = True):
    conf = BonfireConfig()
    clock = Signal(bool(0))
    reset = ResetSignal(0, active=1, isasync=False)
    tck = Signal(bool(0))
    trstn = Signal(bool(1))
    tms = Signal(bool(1))
    tdi = Signal(bool(0))
    tdo = Signal(bool(0))
    dtm = DmiBundle(conf)
    last_scan = Signal(modbv(0)[conf.dmi_adr_width + 34:])
    regs = [Signal(modbv(0)[32:]) for _ in range(2**conf.dmi_adr_width)]
    jtagg_i = Ecp5JtaggInputBundle()
    jtagg_o = Ecp5JtaggOutputBundle()

    clk_driver = ClkDriver(clock, period=10)
    tap = Ecp5JtaggTapEmulator().createInstance(clock, reset, tck, tms, tdi, trstn, tdo, jtagg_i, jtagg_o)
    client = Ecp5JtaggClient(conf, clock, reset, jtagg_i, jtagg_o, dtm)

    @always_seq(clock.posedge, reset=None)
    def dmi_model():
        dtm.dbo.next = 0
        if dtm.en:
            if dtm.we:
                regs[dtm.adr].next = dtm.dbi
                if verbose:
                    print("@{}ns [ecp5-dmi-model] write adr={} data={}".format(now(), hex(int(dtm.adr)), hex(int(dtm.dbi))))
            else:
                dtm.dbo.next = regs[dtm.adr]
                if verbose:
                    print("@{}ns [ecp5-dmi-model] read adr={} data={}".format(now(), hex(int(dtm.adr)), hex(int(regs[dtm.adr]))))

    @instance
    def stimulus() -> Generator[object, None, None]:
        bfm = JtagBFM(tck, tms, tdi, tdo, last_scan, verbose=verbose)
        dmi_width = conf.dmi_adr_width + 34

        regs[0x11].next = 0xA5A55A5A

        trstn.next = False
        yield clock.posedge
        yield clock.posedge
        trstn.next = True
        yield bfm.reset()

        yield bfm.set_ir(ECP5_JTAG_INSTR_IDCODE, width=ECP5_JTAGG_IR_WIDTH)
        yield bfm.scan_dr(0, 32)
        assert int(bfm.last_scan) == ECP5_JTAG_IDCODE_DEFAULT, "ECP5 emulated IDCODE mismatch"

        yield bfm.set_ir(ECP5_JTAGG_IR_ER2, width=ECP5_JTAGG_IR_WIDTH)
        yield bfm.scan_dr(0, 32)
        dtmcs = modbv(int(bfm.last_scan))[32:]
        assert dtmcs[3:0] == 1
        assert dtmcs[9:4] == conf.dmi_adr_width
        assert dtmcs[12:10] == 0
        assert dtmcs[15:12] == DTM_IDLE

        yield bfm.scan_dr(1 << 16, 32)
        yield bfm.scan_dr(0, 32)
        dtmcs = modbv(int(bfm.last_scan))[32:]
        assert dtmcs[12:10] == 0

        yield bfm.set_ir(ECP5_JTAG_INSTR_BYPASS, width=ECP5_JTAGG_IR_WIDTH)
        yield bfm.scan_dr(0b101101, 6)
        assert (int(bfm.last_scan) & 0x3F) == 0b011010

        yield bfm.set_ir(ECP5_JTAGG_IR_ER1, width=ECP5_JTAGG_IR_WIDTH)
        write_scan = (0x10 << 34) | (0x12345678 << 2) | DMI_OP_WRITE
        yield bfm.scan_dr(write_scan, dmi_width)
        previous = modbv(int(bfm.last_scan))[dmi_width:]
        assert previous[2:0] == 0
        yield bfm.idle(2)
        assert regs[0x10] == 0x12345678

        read_scan = (0x10 << 34) | DMI_OP_READ
        yield bfm.scan_dr(read_scan, dmi_width)
        yield bfm.idle(2)
        yield bfm.scan_dr(0, dmi_width)
        response = modbv(int(bfm.last_scan))[dmi_width:]
        assert response[2:0] == 0
        assert response[34:2] == 0x12345678
        assert response[dmi_width:34] == 0x10

        yield bfm.scan_dr((0x11 << 34) | DMI_OP_READ, dmi_width)
        yield bfm.idle(2)
        yield bfm.scan_dr(0, dmi_width)
        response = modbv(int(bfm.last_scan))[dmi_width:]
        assert response[34:2] == 0xA5A55A5A

        raise StopSimulation

    return instances()

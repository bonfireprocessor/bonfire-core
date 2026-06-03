"""
JTAG DTM testbench helpers.
"""
from __future__ import annotations

from collections.abc import Generator
from typing import Any

from myhdl import *

from rtl.config import BonfireConfig
from rtl.debugModule import AbstractDebugTransportBundle
from rtl.type_aliases import BitSignal
from rtl.jtag_dtm import (
    DMI_OP_READ,
    DMI_OP_WRITE,
    JTAG_IDCODE,
    JTAG_INSTR_DMI,
    JTAG_INSTR_DTMCS,
    JTAG_INSTR_IDCODE,
    JTAG_IR_WIDTH,
    JtagDTM,
)


def _bits_lsb_first(value: int, width: int) -> list[int]:
    return [(value >> bit) & 1 for bit in range(width)]


class JtagBFM:
    def __init__(self, tck: BitSignal, tms: BitSignal, tdi: BitSignal, tdo: BitSignal, last_scan: Any, verbose: bool = True) -> None:
        self.tck = tck
        self.tms = tms
        self.tdi = tdi
        self.tdo = tdo
        self.last_tdo = 0
        self.last_scan = last_scan
        self.verbose = verbose

    def log(self, message: str) -> None:
        if self.verbose:
            print("@{}ns [jtag-bfm] {}".format(now(), message))

    def cycle(self, tms: int, tdi: int = 0) -> Generator[Any, None, None]:
        self.tms.next = bool(tms)
        self.tdi.next = bool(tdi)
        yield delay(1)
        self.last_tdo = int(self.tdo)
        self.tck.next = True
        yield delay(5)
        self.tck.next = False
        yield delay(5)

    def reset(self) -> Generator[Any, None, None]:
        self.log("reset TAP with TMS high for 6 TCK cycles")
        for _ in range(6):
            yield self.cycle(1)
        yield self.cycle(0)
        self.log("TAP moved to Run-Test/Idle")

    def set_ir(self, instruction: int) -> Generator[Any, None, None]:
        self.log("IR scan start: instruction={}".format(hex(instruction)))
        yield self.cycle(1)
        yield self.cycle(1)
        yield self.cycle(0)
        yield self.cycle(0)
        bits = _bits_lsb_first(instruction, JTAG_IR_WIDTH)
        for index, bit in enumerate(bits):
            yield self.cycle(1 if index == len(bits) - 1 else 0, bit)
        yield self.cycle(1)
        yield self.cycle(0)
        self.log("IR scan complete: instruction={}".format(hex(instruction)))

    def scan_dr(self, value: int, width: int) -> Generator[Any, None, None]:
        result = 0
        self.log("DR scan start: width={} tdi={}".format(width, hex(value)))
        yield self.cycle(1)
        yield self.cycle(0)
        yield self.cycle(0)
        bits = _bits_lsb_first(value, width)
        for index, bit in enumerate(bits):
            yield self.cycle(1 if index == len(bits) - 1 else 0, bit)
            result |= self.last_tdo << index
        yield self.cycle(1)
        yield self.cycle(0)
        self.last_scan.next = result
        yield delay(0)
        self.log("DR scan complete: tdo={}".format(hex(result)))

    def idle(self, cycles: int = 1) -> Generator[Any, None, None]:
        self.log("idle for {} TCK cycles".format(cycles))
        for _ in range(cycles):
            yield self.cycle(0)


@block
def jtag_dtm_testbench(verbose: bool = True):
    conf = BonfireConfig()
    tck = Signal(bool(0))
    trst = ResetSignal(0, active=1, isasync=True)
    tms = Signal(bool(1))
    tdi = Signal(bool(0))
    tdo = Signal(bool(0))
    dtm = AbstractDebugTransportBundle(conf)
    last_scan = Signal(modbv(0)[conf.dmi_adr_width + 34:])
    regs = [Signal(modbv(0)[32:]) for _ in range(2**conf.dmi_adr_width)]

    dut = JtagDTM(conf).createInstance(tck, trst, tms, tdi, tdo, dtm)

    @always_seq(tck.posedge, reset=None)
    def dmi_model():
        dtm.dbo.next = 0
        if dtm.en:
            if dtm.we:
                regs[dtm.adr].next = dtm.dbi
                if verbose:
                    print("@{}ns [dmi-model] write adr={} data={}".format(now(), hex(int(dtm.adr)), hex(int(dtm.dbi))))
            else:
                dtm.dbo.next = regs[dtm.adr]
                if verbose:
                    print("@{}ns [dmi-model] read adr={} data={}".format(now(), hex(int(dtm.adr)), hex(int(regs[dtm.adr]))))

    @instance
    def stimulus():
        bfm = JtagBFM(tck, tms, tdi, tdo, last_scan, verbose=verbose)
        dmi_width = conf.dmi_adr_width + 34

        regs[0x11].next = 0xA5A55A5A
        print("@{}ns [jtag-tb] starting JTAG DTM testbench".format(now()))
        print("@{}ns [jtag-tb] dmi_width={} abits={}".format(now(), dmi_width, conf.dmi_adr_width))

        trst.next = True
        print("@{}ns [jtag-tb] assert TRST".format(now()))
        yield delay(15)
        trst.next = False
        print("@{}ns [jtag-tb] deassert TRST".format(now()))
        yield bfm.reset()

        yield bfm.set_ir(JTAG_INSTR_IDCODE)
        yield bfm.scan_dr(0, 32)
        idcode = int(bfm.last_scan)
        print("@{}ns [jtag-tb] IDCODE read {}".format(now(), hex(idcode)))
        assert idcode == JTAG_IDCODE, "IDCODE mismatch: got {} expected {}".format(hex(idcode), hex(JTAG_IDCODE))

        yield bfm.set_ir(JTAG_INSTR_DTMCS)
        yield bfm.scan_dr(0, 32)
        dtmcs = modbv(int(bfm.last_scan))[32:]
        print("@{}ns [jtag-tb] DTMCS read {} version={} abits={} idle={}".format(now(), hex(int(dtmcs)), int(dtmcs[3:0]), int(dtmcs[9:4]), int(dtmcs[12:10])))
        assert dtmcs[3:0] == 1
        assert dtmcs[9:4] == conf.dmi_adr_width

        yield bfm.set_ir(JTAG_INSTR_DMI)
        write_scan = (0x10 << 34) | (0x12345678 << 2) | DMI_OP_WRITE
        print("@{}ns [jtag-tb] DMI write request adr=0x10 data=0x12345678".format(now()))
        yield bfm.scan_dr(write_scan, dmi_width)
        previous = modbv(int(bfm.last_scan))[dmi_width:]
        print("@{}ns [jtag-tb] DMI previous response {}".format(now(), hex(int(previous))))
        assert previous[2:0] == 0
        yield bfm.idle(2)
        assert regs[0x10] == 0x12345678
        print("@{}ns [jtag-tb] DMI write observed in model".format(now()))

        read_scan = (0x10 << 34) | DMI_OP_READ
        print("@{}ns [jtag-tb] DMI read request adr=0x10".format(now()))
        yield bfm.scan_dr(read_scan, dmi_width)
        yield bfm.idle(2)
        yield bfm.scan_dr(0, dmi_width)
        read_response = modbv(int(bfm.last_scan))[dmi_width:]
        print("@{}ns [jtag-tb] DMI read response adr={} data={} op={}".format(now(), hex(int(read_response[dmi_width:34])), hex(int(read_response[34:2])), int(read_response[2:0])))
        assert read_response[2:0] == 0
        assert read_response[34:2] == 0x12345678
        assert read_response[dmi_width:34] == 0x10

        print("@{}ns [jtag-tb] DMI read request adr=0x11".format(now()))
        yield bfm.scan_dr((0x11 << 34) | DMI_OP_READ, dmi_width)
        yield bfm.idle(2)
        yield bfm.scan_dr(0, dmi_width)
        read_response = modbv(int(bfm.last_scan))[dmi_width:]
        print("@{}ns [jtag-tb] DMI read response adr={} data={} op={}".format(now(), hex(int(read_response[dmi_width:34])), hex(int(read_response[34:2])), int(read_response[2:0])))
        assert read_response[34:2] == 0xA5A55A5A

        print("@{}ns [jtag-tb] completed JTAG DTM testbench".format(now()))
        raise StopSimulation

    return instances()

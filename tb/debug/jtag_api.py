"""
JTAG-based debug API.
(c) 2023-2026 The Bonfire Project
License: See LICENSE
"""
from __future__ import annotations

from collections.abc import Generator

from myhdl import delay, modbv, now

from rtl.config import BonfireConfig
from rtl.debug.jtag_dtm import (
    DTM_IDLE,
    DTM_VERSION,
    DMI_OP_READ,
    DMI_OP_WRITE,
    JTAG_IDCODE,
    JTAG_INSTR_DMI,
    JTAG_INSTR_DTMCS,
    JTAG_INSTR_IDCODE,
    JTAG_IR_WIDTH,
)
from rtl.type_aliases import BitSignal
from tb.debug.debug_api import DebugAPI


def _bits_lsb_first(value: int, width: int) -> list[int]:
    return [(value >> bit) & 1 for bit in range(width)]


class JtagDebugAPI(DebugAPI):
    def __init__(
        self,
        config: BonfireConfig,
        clock: BitSignal,
        tck: BitSignal,
        tms: BitSignal,
        tdi: BitSignal,
        tdo: BitSignal,
        verbose: bool = False,
        ir_width: int = JTAG_IR_WIDTH,
        ir_idcode: int = JTAG_INSTR_IDCODE,
        ir_dtmcs: int = JTAG_INSTR_DTMCS,
        ir_dmi: int = JTAG_INSTR_DMI,
        expected_idcode: int = JTAG_IDCODE,
    ) -> None:
        self.clock = clock
        self.tck = tck
        self.tms = tms
        self.tdi = tdi
        self.tdo = tdo
        self.verbose = verbose
        self.last_tdo = 0
        self.last_scan = 0
        self.dtmcs = 0
        self.idcode = 0
        self.tck_low_aligned = False
        self.dmi_width = config.dmi_adr_width + 34
        self.ir_width = ir_width
        self.ir_idcode = ir_idcode
        self.ir_dtmcs = ir_dtmcs
        self.ir_dmi = ir_dmi
        self.expected_idcode = expected_idcode
        self.settle_sysclk_cycles = 3
        DebugAPI.__init__(self, config=config)

    def log(self, message: str) -> None:
        if self.verbose:
            print("@{}ns [jtag-debug-api] {}".format(now(), message))

    def yield_clock(self) -> Generator[object, None, None]:
        yield self.clock.posedge

    def wait_sysclk(self, cycles: int) -> Generator[object, None, None]:
        for _ in range(cycles):
            yield self.clock.posedge
            yield delay(0)

    def align_tck_low(self) -> Generator[object, None, None]:
        if not self.tck_low_aligned:
            yield self.tck.negedge
            self.tck_low_aligned = True

    def jtag_cycle(self, tms: int, tdi: int = 0) -> Generator[object, None, None]:
        yield self.align_tck_low()
        self.tms.next = bool(tms)
        self.tdi.next = bool(tdi)
        yield delay(0)
        self.last_tdo = int(self.tdo)
        yield self.tck.posedge
        yield self.tck.negedge
        yield self.wait_sysclk(self.settle_sysclk_cycles)

    def reset_tap(self) -> Generator[object, None, None]:
        self.log("reset TAP")
        for _ in range(6):
            yield self.jtag_cycle(1)
        yield self.jtag_cycle(0)

    def read_idcode(self) -> Generator[object, None, int]:
        yield self.set_ir(self.ir_idcode)
        yield self.scan_dr(0, 32)
        self.idcode = self.last_scan
        assert self.idcode == self.expected_idcode, "JTAG IDCODE mismatch: got {} expected {}".format(hex(self.idcode), hex(self.expected_idcode))
        self.log("JTAG IDCODE {}".format(hex(self.idcode)))
        return self.idcode

    def read_dtmcs(self) -> Generator[object, None, int]:
        yield self.set_ir(self.ir_dtmcs)
        yield self.scan_dr(0, 32)
        self.dtmcs = self.last_scan
        dtmcs = modbv(self.dtmcs)[32:]
        assert dtmcs[3:0] == DTM_VERSION, "DTMCS version: {} expected {}".format(int(dtmcs[3:0]), DTM_VERSION)
        assert dtmcs[9:4] == self.config.dmi_adr_width, "DTMCS abits: {} expected {}".format(int(dtmcs[9:4]), self.config.dmi_adr_width)
        assert dtmcs[12:10] == 0, "DTMCS dmistat: {} expected 0".format(int(dtmcs[12:10]))
        assert dtmcs[15:12] == DTM_IDLE, "DTMCS idle: {} expected {}".format(int(dtmcs[15:12]), DTM_IDLE)
        self.log("DTMCS {}".format(hex(self.dtmcs)))
        return self.dtmcs

    def set_ir(self, instruction: int) -> Generator[object, None, None]:
        self.log("set IR {}".format(hex(instruction)))
        yield self.jtag_cycle(1)
        yield self.jtag_cycle(1)
        yield self.jtag_cycle(0)
        yield self.jtag_cycle(0)
        bits = _bits_lsb_first(instruction, self.ir_width)
        for index, bit in enumerate(bits):
            yield self.jtag_cycle(1 if index == len(bits) - 1 else 0, bit)
        yield self.jtag_cycle(1)
        yield self.jtag_cycle(0)

    def scan_dr(self, value: int, width: int) -> Generator[object, None, None]:
        result = 0
        yield self.jtag_cycle(1)
        yield self.jtag_cycle(0)
        yield self.jtag_cycle(0)
        bits = _bits_lsb_first(value, width)
        for index, bit in enumerate(bits):
            yield self.jtag_cycle(1 if index == len(bits) - 1 else 0, bit)
            result |= self.last_tdo << index
        yield self.jtag_cycle(1)
        yield self.jtag_cycle(0)
        self.last_scan = result

    def idle(self, cycles: int = 1) -> Generator[object, None, None]:
        for _ in range(cycles):
            yield self.jtag_cycle(0)

    def dmi_read(self, adr: int) -> Generator[object, None, None]:
        yield self.set_ir(self.ir_dmi)
        request = (adr << 34) | DMI_OP_READ
        self.log("DMI read request adr={}".format(hex(adr)))
        yield self.scan_dr(request, self.dmi_width)
        yield self.idle(2)
        yield self.scan_dr(0, self.dmi_width)
        response = modbv(self.last_scan)[self.dmi_width:]
        op = response[2:0]
        assert op == 0, "JTAG DMI read failed with op {}".format(op)
        self.result._val = response[34:2]
        self.log("DMI read response adr={} data={}".format(hex(adr), hex(self.cmd_result())))

    def dmi_write(self, adr: int, data: int) -> Generator[object, None, None]:
        yield self.set_ir(self.ir_dmi)
        request = (adr << 34) | (data << 2) | DMI_OP_WRITE
        self.log("DMI write adr={} data={}".format(hex(adr), hex(data)))
        yield self.scan_dr(request, self.dmi_width)
        response = modbv(self.last_scan)[self.dmi_width:]
        op = response[2:0]
        assert op == 0, "JTAG DMI write failed with op {}".format(op)
        yield self.idle(2)

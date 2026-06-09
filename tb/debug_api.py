"""
RISC-V Debug Api
(c) 2023-2026 The Bonfire Project
License: See LICENSE
"""
from __future__ import annotations, print_function

from collections.abc import Generator
from typing import Any

from myhdl import *

from rtl.config import BonfireConfig
from rtl.jtag_dtm import (
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

EBREAK_INSN = 0x00100073
CSR_OPCODE = 0x73
CSRRS_FUNCT3 = 0x2
CSRRW_FUNCT3 = 0x1
CSR_SCRATCH_GPR = 8


def encode_csrr(rd: int, csr_adr: int) -> int:
    return (csr_adr << 20) | (CSRRS_FUNCT3 << 12) | (rd << 7) | CSR_OPCODE


def encode_csrw(csr_adr: int, rs1: int) -> int:
    return (csr_adr << 20) | (rs1 << 15) | (CSRRW_FUNCT3 << 12) | CSR_OPCODE


class DebugAPI:
    def __init__(self, config: BonfireConfig | None = None) -> None:
        self.config = config or BonfireConfig()
        self.halted: bool = False
        self.result: Any = modbv(0)[32:]
        self.cmderr: int = 0

    def __not_implemented(self) -> None:
        raise Exception("Not Implemented")

    def cmd_result(self) -> int:
        return self.result + 0

    def yield_clock(self) -> Generator[Any, None, None]:
        print("Warning: DebugAPI.yield_clock called")
        if False:
            yield None

    def check_halted(self, HartId: int = 0) -> Generator[Any, None, None]:
        yield self.dmi_read(0x11)
        self.halted = self.result[8]

    def wait_resume_ack(self, HartId: int = 0) -> Generator[Any, None, None]:
        ack = False
        while not ack:
            yield self.dmi_read(0x11)
            ack = self.result[16]

    def halt(self, HartId: int = 0) -> Generator[Any, None, bool]:
        yield self.check_halted()
        if not self.halted:
            c = modbv(0x80000000)[32:]
            yield self.dmi_write(0x10, c)
            while not self.halted:
                yield self.check_halted()

        return True

    def resume(self, HartId: int = 0) -> Generator[Any, None, None]:
        yield self.check_halted()
        if self.halted:
            c = modbv(0)[32:]
            c[30] = True
            yield self.dmi_write(0x10, c)
            yield self.wait_resume_ack()
            yield self.check_halted()
            assert not self.halted, "debug_api.resume error: Core still halted after resume_ack"

    def dmi_read(self, adr: int) -> Generator[Any, None, None]:
        self.__not_implemented()
        yield None

    def dmi_write(self, adr: int, data: int) -> Generator[Any, None, None]:
        self.__not_implemented()
        yield None

    def writeProgbuf0(self, instruction: int) -> Generator[Any, None, None]:
        yield self.dmi_write(0x20, instruction)
        if self.config.progbuf_size == 2:
            yield self.dmi_write(0x21, EBREAK_INSN)

    def readReg(
        self,
        HartId: int = 0,
        regno: int = 0,
        postexec: bool = False,
        transfer: bool = True,
        AssertCmdErr: bool = True,
    ) -> Generator[Any, None, None]:
        c = modbv(0)[32:]
        c[23:20] = 2  # aarsize 32Bit
        c[15:0] = regno
        c[17] = transfer
        c[18] = postexec
        yield self.dmi_write(0x17, c)
        yield self.yield_clock()
        yield self.dmi_read(0x16)  # abstractcs

        while self.result[12]:
            yield self.dmi_read(0x16)

        self.cmderr = self.result[11:8]
        if AssertCmdErr:
            assert self.cmderr == 0, "readReg command failed"
        if self.cmderr == 0:
            yield self.dmi_read(0x4)

    def readGPR(
        self,
        HartId: int = 0,
        regno: int = 1,
        postexec: bool = False,
        transfer: bool = True,
    ) -> Generator[Any, None, None]:
        yield self.readReg(HartId=HartId, regno=regno + 0x1000, postexec=postexec, transfer=transfer)

    def writeReg(
        self,
        HartId: int = 0,
        regno: int = 0,
        value: int = 0,
        postexec: bool = False,
        transfer: bool = True,
        AssertCmdErr: bool = True,
    ) -> Generator[Any, None, None]:
        yield self.dmi_write(0x4, value)

        c = modbv(0)[32:]
        c[23:20] = 2  # aarsize 32Bit
        c[15:0] = regno
        c[17] = transfer
        c[18] = postexec
        c[16] = True  # Write
        yield self.dmi_write(0x17, c)
        yield self.yield_clock()
        yield self.dmi_read(0x16)

        while self.result[12]:
            yield self.dmi_read(0x16)

        self.cmderr = self.result[11:8]
        if AssertCmdErr:
            assert self.cmderr == 0, "writeReg command failed"

    def writeGPR(
        self,
        HartId: int = 0,
        regno: int = 1,
        value: int = 0,
        postexec: bool = False,
        transfer: bool = True,
    ) -> Generator[Any, None, None]:
        yield self.writeReg(HartId=HartId, regno=regno + 0x1000, value=value, postexec=postexec, transfer=transfer)

    def readCSR(self, csr_adr: int, scratch_reg: int = CSR_SCRATCH_GPR) -> Generator[Any, None, None]:
        yield self.readGPR(regno=scratch_reg)
        scratch_save = self.cmd_result()
        yield self.writeProgbuf0(encode_csrr(scratch_reg, csr_adr))
        yield self.readReg(transfer=False, postexec=True)
        yield self.readGPR(regno=scratch_reg)
        csr_value = self.cmd_result()
        yield self.writeGPR(regno=scratch_reg, value=scratch_save)
        self.result = modbv(csr_value)[32:]

    def writeCSR(self, csr_adr: int, value: int, scratch_reg: int = CSR_SCRATCH_GPR) -> Generator[Any, None, None]:
        yield self.readGPR(regno=scratch_reg)
        scratch_save = self.cmd_result()
        yield self.writeGPR(regno=scratch_reg, value=value)
        yield self.writeProgbuf0(encode_csrw(csr_adr, scratch_reg))
        yield self.readReg(transfer=False, postexec=True)
        yield self.writeGPR(regno=scratch_reg, value=scratch_save)

    def ResetCore(self) -> None:
        c = modbv(0)[32:]
        c[1] = True
        self.dmi_write(0x10, c)
        c[1] = False
        self.dmi_write(0x10, c)

    def readMemory(self, HartId: int = 0, memadr: int = 0, readbyte: bool = False) -> Generator[Any, None, None]:
        yield self.writeProgbuf0(0x00044403 if readbyte else 0x00042403)
        yield self.writeGPR(regno=8, value=memadr, postexec=True, transfer=True)
        yield self.readGPR(regno=8, transfer=True)

    def writeMemory(
        self,
        HartId: int = 0,
        memadr: int = 0,
        memvalue: int = 0,
        writeByte: bool = False,
    ) -> Generator[Any, None, None]:
        yield self.writeProgbuf0(0x00940023 if writeByte else 0x00942023)
        yield self.writeGPR(regno=8, value=memadr, transfer=True)
        yield self.writeGPR(regno=9, value=memvalue, postexec=True, transfer=True)


class DebugAPISim(DebugAPI):
    def __init__(self, dtm_bundle: Any, clock: Any, config: BonfireConfig | None = None) -> None:
        self.dtm_bundle = dtm_bundle
        self.clock = clock
        DebugAPI.__init__(self, config=config)

    def yield_clock(self) -> Generator[Any, None, None]:
        yield self.clock.posedge

    def dmi_read(self, adr: int) -> Generator[Any, None, None]:
        yield self.clock.posedge
        self.dtm_bundle.adr.next = adr
        self.dtm_bundle.we.next = False
        self.dtm_bundle.en.next = True
        yield self.clock.posedge
        yield self.clock.posedge
        self.result._val = self.dtm_bundle.dbo
        self.dtm_bundle.en.next = False

    def dmi_write(self, adr: int, data: int) -> Generator[Any, None, None]:
        yield self.clock.posedge
        self.dtm_bundle.adr.next = adr
        self.dtm_bundle.we.next = True
        self.dtm_bundle.en.next = True
        self.dtm_bundle.dbi.next = data
        yield self.clock.posedge
        self.dtm_bundle.en.next = False


def _bits_lsb_first(value: int, width: int) -> list[int]:
    return [(value >> bit) & 1 for bit in range(width)]


class JtagDebugAPISim(DebugAPI):
    def __init__(
        self,
        config: BonfireConfig,
        clock: BitSignal,
        tck: BitSignal,
        tms: BitSignal,
        tdi: BitSignal,
        tdo: BitSignal,
        verbose: bool = False,
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
        DebugAPI.__init__(self, config=config)

    def log(self, message: str) -> None:
        if self.verbose:
            print("@{}ns [jtag-debug-api] {}".format(now(), message))

    def yield_clock(self) -> Generator[Any, None, None]:
        yield self.clock.posedge

    def wait_sysclk(self, cycles: int) -> Generator[Any, None, None]:
        for _ in range(cycles):
            yield self.clock.posedge
            yield delay(0)

    def align_tck_low(self) -> Generator[Any, None, None]:
        if not self.tck_low_aligned:
            yield self.tck.negedge
            self.tck_low_aligned = True

    def jtag_cycle(self, tms: int, tdi: int = 0) -> Generator[Any, None, None]:
        yield self.align_tck_low()
        self.tms.next = bool(tms)
        self.tdi.next = bool(tdi)
        yield delay(0)
        self.last_tdo = int(self.tdo)
        yield self.tck.posedge
        yield self.tck.negedge
        yield self.wait_sysclk(3)

    def reset_tap(self) -> Generator[Any, None, None]:
        self.log("reset TAP")
        for _ in range(6):
            yield self.jtag_cycle(1)
        yield self.jtag_cycle(0)

    def read_idcode(self) -> Generator[Any, None, int]:
        yield self.set_ir(JTAG_INSTR_IDCODE)
        yield self.scan_dr(0, 32)
        self.idcode = self.last_scan
        assert self.idcode == JTAG_IDCODE, "JTAG IDCODE mismatch: got {} expected {}".format(hex(self.idcode), hex(JTAG_IDCODE))
        self.log("JTAG IDCODE {}".format(hex(self.idcode)))
        return self.idcode

    def read_dtmcs(self) -> Generator[Any, None, int]:
        yield self.set_ir(JTAG_INSTR_DTMCS)
        yield self.scan_dr(0, 32)
        self.dtmcs = self.last_scan
        dtmcs = modbv(self.dtmcs)[32:]
        assert dtmcs[3:0] == DTM_VERSION, "DTMCS version: {} expected {}".format(int(dtmcs[3:0]), DTM_VERSION)
        assert dtmcs[9:4] == self.config.dmi_adr_width, "DTMCS abits: {} expected {}".format(int(dtmcs[9:4]), self.config.dmi_adr_width)
        assert dtmcs[12:10] == 0, "DTMCS dmistat: {} expected 0".format(int(dtmcs[12:10]))
        assert dtmcs[15:12] == DTM_IDLE, "DTMCS idle: {} expected {}".format(int(dtmcs[15:12]), DTM_IDLE)
        self.log("DTMCS {}".format(hex(self.dtmcs)))
        return self.dtmcs

    def set_ir(self, instruction: int) -> Generator[Any, None, None]:
        self.log("set IR {}".format(hex(instruction)))
        yield self.jtag_cycle(1)
        yield self.jtag_cycle(1)
        yield self.jtag_cycle(0)
        yield self.jtag_cycle(0)
        bits = _bits_lsb_first(instruction, JTAG_IR_WIDTH)
        for index, bit in enumerate(bits):
            yield self.jtag_cycle(1 if index == len(bits) - 1 else 0, bit)
        yield self.jtag_cycle(1)
        yield self.jtag_cycle(0)

    def scan_dr(self, value: int, width: int) -> Generator[Any, None, None]:
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

    def idle(self, cycles: int = 1) -> Generator[Any, None, None]:
        for _ in range(cycles):
            yield self.jtag_cycle(0)

    def dmi_read(self, adr: int) -> Generator[Any, None, None]:
        yield self.set_ir(JTAG_INSTR_DMI)
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

    def dmi_write(self, adr: int, data: int) -> Generator[Any, None, None]:
        yield self.set_ir(JTAG_INSTR_DMI)
        request = (adr << 34) | (data << 2) | DMI_OP_WRITE
        self.log("DMI write adr={} data={}".format(hex(adr), hex(data)))
        yield self.scan_dr(request, self.dmi_width)
        response = modbv(self.last_scan)[self.dmi_width:]
        op = response[2:0]
        assert op == 0, "JTAG DMI write failed with op {}".format(op)
        yield self.idle(2)

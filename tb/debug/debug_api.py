"""
Transport-independent RISC-V debug API.
(c) 2023-2026 The Bonfire Project
License: See LICENSE
"""
from __future__ import annotations, print_function

from collections.abc import Generator
from typing import Any

from myhdl import modbv

from rtl.config import BonfireConfig

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
        c[23:20] = 2
        c[15:0] = regno
        c[17] = transfer
        c[18] = postexec
        yield self.dmi_write(0x17, c)
        yield self.yield_clock()
        yield self.dmi_read(0x16)

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
        c[23:20] = 2
        c[15:0] = regno
        c[17] = transfer
        c[18] = postexec
        c[16] = True
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

    def ResetCore(self) -> Generator[Any, None, None]:
        # Assert ndmreset (bit 1) while keeping dmactive (bit 0) set.
        c = modbv(0)[32:]
        c[1] = True   # ndmreset
        c[0] = True   # dmactive
        yield self.dmi_write(0x10, c)
        # De-assert ndmreset to let the core come out of reset.
        c = modbv(0)[32:]
        c[0] = True   # dmactive
        yield self.dmi_write(0x10, c)

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

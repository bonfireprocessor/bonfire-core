"""
RISC-V Debug Api
(c) 2023 The Bonfire Project
License: See LICENSE
"""
from __future__ import annotations, print_function

from collections.abc import Generator
from typing import Any

from myhdl import *


class DebugAPI:
    def __init__(self) -> None:
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

    def ResetCore(self) -> None:
        c = modbv(0)[32:]
        c[1] = True
        self.dmi_write(0x10, c)
        c[1] = False
        self.dmi_write(0x10, c)

    def readMemory(self, HartId: int = 0, memadr: int = 0, readbyte: bool = False) -> Generator[Any, None, None]:
        yield self.dmi_write(0x20, (0x00044403 if readbyte else 0x00042403))
        yield self.writeGPR(regno=8, value=memadr, postexec=True, transfer=True)
        yield self.readGPR(regno=8, transfer=True)

    def writeMemory(
        self,
        HartId: int = 0,
        memadr: int = 0,
        memvalue: int = 0,
        writeByte: bool = False,
    ) -> Generator[Any, None, None]:
        yield self.dmi_write(0x20, 0x00940023 if writeByte else 0x00942023)
        yield self.writeGPR(regno=8, value=memadr, transfer=True)
        yield self.writeGPR(regno=9, value=memvalue, postexec=True, transfer=True)


class DebugAPISim(DebugAPI):
    def __init__(self, dtm_bundle: Any, clock: Any) -> None:
        self.dtm_bundle = dtm_bundle
        self.clock = clock
        DebugAPI.__init__(self)

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

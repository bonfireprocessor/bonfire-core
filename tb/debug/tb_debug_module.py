"""
Bonfire Core debug module testbench
(c) 2019,2020 The Bonfire Project
License: See LICENSE
"""

from __future__ import annotations, print_function

from collections.abc import Generator
from math import log
from typing import Any

from myhdl import *

from rtl import bonfire_core_top, bonfire_interfaces, config
from rtl.debug import DmiBundle, DEBUG_SPEC_VERSION, Ecp5JtaggClient, Ecp5JtaggInputBundle, Ecp5JtaggOutputBundle, Ecp5JtaggTapEmulator
from rtl.instructions import CSRAdr
from rtl.debug.jtag_dtm import JtagDTM
from tb.ClkDriver import ClkDriver
from tb.debug import DebugAPI, DmiDebugAPI, Ecp5JtaggDebugAPI, JtagDebugAPI
from tb.disassemble import abi_name, disassemble
from tb.sim_monitor import monitor_instance
from tb.sim_ram import sim_ram

CSRR_A0_DCSR = 0x7B002573
CSRR_A0_DPC = 0x7B102573
CSRW_DCSR_A0 = 0x7B051073
CSRW_DCSR_S0 = 0x7B041073
CSRW_DPC_A0 = 0x7B151073
EBREAK = 0x00100073
ECALL = 0x00000073
FENCE = 0x0000000F
DEBUG_LOOP_J = 0x0000006F
BEQ_ZERO_ZERO_PLUS_8 = 0x00000463
BNE_ZERO_ZERO_PLUS_8 = 0x00001463
BLTU_T0_T1_MINUS_8 = 0xFE62ECE3


class BonfireCoreDebugTestbench:
    def __init__(
        self,
        config: config.BonfireConfig = config.BonfireConfig(),
        hexfile: str = "",
        elfFile: str = "",
        sigFile: str = "",
        ramsize: int = 16384,
        verbose: bool = False,
        debug_transport: str = "dmi",
        monitor_result: Any = None,
        stimulus_mode: str = "full",
    ) -> None:
        self.config = config
        self.hexfile = hexfile
        self.elfFile = elfFile
        self.sigFile = sigFile
        self.ramsize = ramsize
        self.verbose = verbose
        self.debug_transport = debug_transport
        self.monitor_result = monitor_result
        self.stimulus_mode = stimulus_mode

    def log(self, message: str) -> None:
        print("@{}ns [debug-tb] {}".format(now(), message))

    def create_ram(self, progfile: str, ramsize: int) -> list[Any]:
        ram: list[Any] = []
        adr = 0

        with open(progfile, "r") as f:
            for line in f:
                i = int(line, 16)
                ram.append(Signal(intbv(i)[32:]))
                adr += 1

        print("eof at adr:{}".format(hex(adr << 2)))
        for _ in range(adr, ramsize):
            ram.append(Signal(intbv(0)[32:]))

        print("Created ram with size {} words".format(len(ram)))
        return ram

    def check_cmd_result(self, api: DebugAPI, check_value: int, text: str = "") -> None:
        assert api.cmd_result() == check_value, "{} result: {} expected: {}".format(text, hex(api.cmd_result()), hex(check_value))
        self.log("{} -> {}".format(text or "cmd result", hex(api.cmd_result())))

    def check_gpr(self, api: DebugAPI, regno: int, check_value: int) -> Generator[Any, None, None]:
        yield api.readGPR(regno=regno)
        assert api.cmd_result() == check_value, "check_gpr failure result: {} expected: {}".format(hex(api.cmd_result()), hex(check_value))
        self.log("verify GPR {} = {}".format(abi_name(regno), hex(api.cmd_result())))

    def set_and_check_dcsr(self, api: DebugAPI, breakm: bool = False, step: bool = False) -> Generator[Any, None, None]:
        dcsr = 0x700 | CSRAdr.dcsr
        v = modbv(0)[32:]
        v[15] = breakm
        v[2] = step
        yield api.writeCSR(csr_adr=dcsr, value=v)
        yield api.readCSR(csr_adr=dcsr)
        self.log("dcsr = {} (ebreakm={}, step={})".format(hex(api.cmd_result()), breakm, step))
        assert api.result[15] == breakm and api.result[2] == step, "dcsr write failed"

    def check_dpc(self, api: DebugAPI, expected: int, text: str) -> Generator[Any, None, None]:
        yield api.readCSR(csr_adr=0x700 | CSRAdr.dpc)
        actual = api.cmd_result()
        self.log("{} dpc = {}".format(text, hex(actual)))
        assert actual == expected, "{} dpc: {} expected: {}".format(text, hex(actual), hex(expected))

    def wait_abstract_idle(self, api: DebugAPI, text: str) -> Generator[Any, None, None]:
        yield api.dmi_read(0x16)
        while api.result[12]:
            yield api.dmi_read(0x16)

        cmderr = api.result[11:8]
        assert cmderr == 0, "{} cmderr: {}".format(text, cmderr)

    def check_abstractauto_memory_read(
        self,
        api: DebugAPI,
        expected0: int,
        expected4: int,
    ) -> Generator[Any, None, None]:
        self.log("testing abstractauto data0 memory read sequence")

        yield api.dmi_write(0x20, 0x00042483)  # lw s1, 0(s0)
        yield api.dmi_write(0x21, 0x00440413)  # addi s0, s0, 4
        yield api.writeGPR(regno=8, value=0, transfer=True)

        yield api.readGPR(regno=9, postexec=True, transfer=True)
        yield api.dmi_write(0x18, 0x00000001)  # abstractauto.autoexecdata0

        yield api.dmi_read(0x04)  # Returns stale data0, starts command for address 0.
        yield self.wait_abstract_idle(api, "abstractauto prime")

        yield api.dmi_read(0x04)  # Returns memory[0], starts command for address 4.
        actual0 = api.cmd_result()
        yield self.wait_abstract_idle(api, "abstractauto memory[0]")

        yield api.dmi_write(0x18, 0x00000000)
        yield api.dmi_read(0x04)
        actual4 = api.cmd_result()

        assert actual0 == expected0, "abstractauto memory[0]: {} expected {}".format(hex(actual0), hex(expected0))
        assert actual4 == expected4, "abstractauto memory[4]: {} expected {}".format(hex(actual4), hex(expected4))
        self.log("abstractauto memory sequence read {} then {}".format(hex(actual0), hex(actual4)))

    def execute_progbuf0(self, api: DebugAPI, opcode: int) -> Generator[Any, None, None]:
        yield api.writeProgbuf0(opcode)
        yield api.readReg(transfer=False, postexec=True)

    def resume_without_running_assert(self, api: DebugAPI) -> Generator[Any, None, None]:
        c = modbv(0)[32:]
        c[30] = True
        yield api.dmi_write(0x10, c)
        yield api.wait_resume_ack()

    def check_debug_csr_instructions(self, api: DebugAPI) -> Generator[Any, None, None]:
        self.log("testing dcsr/dpc access through CSR instructions")

        dcsr_value = modbv(0)[32:]
        dcsr_value[15] = True
        dcsr_value[2] = True
        yield api.writeGPR(regno=10, value=dcsr_value)
        yield self.execute_progbuf0(api, CSRW_DCSR_A0)
        yield self.execute_progbuf0(api, CSRR_A0_DCSR)
        yield api.readGPR(regno=10)
        dcsr_value = modbv(api.cmd_result())[32:]
        assert dcsr_value[32:28] == 4 and dcsr_value[15] and dcsr_value[2], "csr dcsr read failed: {}".format(hex(api.cmd_result()))
        self.log("csr dcsr read = {}".format(hex(api.cmd_result())))

        yield api.writeGPR(regno=10, value=0x14)
        yield self.execute_progbuf0(api, CSRW_DPC_A0)
        yield self.check_dpc(api, 0x14, "csr write dpc")

        yield self.execute_progbuf0(api, CSRR_A0_DPC)
        yield self.check_gpr(api, regno=10, check_value=0x14)

    def check_debug_csr_abstract_access_rejected(self, api: DebugAPI) -> Generator[Any, None, None]:
        self.log("testing that debug CSRs are not accessible through abstract commands")

        yield api.readReg(regno=0x700 | CSRAdr.dcsr, AssertCmdErr=False)
        assert api.cmderr == 2, "abstract dcsr read cmderr: {} expected 2".format(api.cmderr)
        yield api.dmi_write(0x16, 0x00000700)

        yield api.writeReg(regno=0x700 | CSRAdr.dpc, value=0x10, AssertCmdErr=False)
        assert api.cmderr == 2, "abstract dpc write cmderr: {} expected 2".format(api.cmderr)
        yield api.dmi_write(0x16, 0x00000700)

    def check_ebreakm_and_step(self, api: DebugAPI) -> Generator[Any, None, None]:
        self.log("testing ebreakm and single step debug entry")

        yield api.writeMemory(memadr=0x0C, memvalue=EBREAK)
        yield api.writeCSR(csr_adr=0x700 | CSRAdr.dpc, value=0x0C)
        yield self.set_and_check_dcsr(api, breakm=True, step=False)
        yield self.resume_without_running_assert(api)
        yield api.check_halted()
        while not api.halted:
            yield api.check_halted()

        yield self.check_dpc(api, 0x0C, "ebreakm halt")
        yield api.readCSR(csr_adr=0x700 | CSRAdr.dcsr)
        assert api.result[9:6] == 1, "ebreakm dcsr cause: {} expected 1".format(int(api.result[9:6]))
        yield api.writeMemory(memadr=0x0C, memvalue=DEBUG_LOOP_J)

        yield api.writeCSR(csr_adr=0x700 | CSRAdr.dpc, value=0x0C)
        yield self.set_and_check_dcsr(api, breakm=False, step=True)
        yield self.resume_without_running_assert(api)
        yield api.check_halted()
        while not api.halted:
            yield api.check_halted()

        yield self.check_dpc(api, 0x0C, "single step jump halt")
        yield api.readCSR(csr_adr=0x700 | CSRAdr.dcsr)
        assert api.result[9:6] == 4, "jump step dcsr cause: {} expected 4".format(int(api.result[9:6]))

        yield api.writeMemory(memadr=0x100, memvalue=BEQ_ZERO_ZERO_PLUS_8)
        yield api.writeCSR(csr_adr=0x700 | CSRAdr.dpc, value=0x100)
        yield self.resume_without_running_assert(api)
        yield api.check_halted()
        while not api.halted:
            yield api.check_halted()
        yield self.check_dpc(api, 0x108, "single step taken branch halt")

        yield api.writeMemory(memadr=0x100, memvalue=BNE_ZERO_ZERO_PLUS_8)
        yield api.writeCSR(csr_adr=0x700 | CSRAdr.dpc, value=0x100)
        yield self.resume_without_running_assert(api)
        yield api.check_halted()
        while not api.halted:
            yield api.check_halted()
        yield self.check_dpc(api, 0x104, "single step not-taken branch halt")

        yield api.writeMemory(memadr=0x108, memvalue=BLTU_T0_T1_MINUS_8)
        yield api.writeGPR(regno=5, value=1)
        yield api.writeGPR(regno=6, value=2)
        yield api.writeCSR(csr_adr=0x700 | CSRAdr.dpc, value=0x108)
        yield self.resume_without_running_assert(api)
        yield api.check_halted()
        while not api.halted:
            yield api.check_halted()
        yield self.check_dpc(api, 0x100, "single step backward taken branch halt")

        # A software breakpoint in the fall-through path of a taken branch is
        # speculative and must not enter Debug Mode. Halt at the breakpoint on
        # the actual branch target instead.
        yield self.set_and_check_dcsr(api, breakm=True, step=False)
        yield api.writeMemory(memadr=0x100, memvalue=EBREAK)
        yield api.writeMemory(memadr=0x108, memvalue=BLTU_T0_T1_MINUS_8)
        yield api.writeMemory(memadr=0x10C, memvalue=EBREAK)
        yield api.writeGPR(regno=5, value=1)
        yield api.writeGPR(regno=6, value=2)
        yield api.writeCSR(csr_adr=0x700 | CSRAdr.dpc, value=0x108)
        yield self.resume_without_running_assert(api)
        yield api.check_halted()
        while not api.halted:
            yield api.check_halted()
        yield self.check_dpc(api, 0x100, "taken branch target breakpoint halt")

        yield self.set_and_check_dcsr(api, breakm=False, step=True)

        yield api.writeMemory(memadr=0x110, memvalue=ECALL)
        yield api.writeCSR(csr_adr=0x300 | CSRAdr.tvec, value=0x120)
        yield api.writeCSR(csr_adr=0x700 | CSRAdr.dpc, value=0x110)
        yield self.resume_without_running_assert(api)
        yield api.check_halted()
        while not api.halted:
            yield api.check_halted()
        yield self.check_dpc(api, 0x120, "single step trap halt")

        # FENCE is implemented as a decode-stage NOP and therefore has no
        # execute-stage valid pulse. Single-step must still stop at its
        # architectural successor.
        yield api.writeMemory(memadr=0x114, memvalue=FENCE)
        yield api.writeCSR(csr_adr=0x700 | CSRAdr.dpc, value=0x114)
        yield self.resume_without_running_assert(api)
        yield api.check_halted()
        while not api.halted:
            yield api.check_halted()
        yield self.check_dpc(api, 0x118, "single step fence halt")

        yield api.writeCSR(csr_adr=0x700 | CSRAdr.dpc, value=0x10)
        dcsr_value = modbv(0)[32:]
        dcsr_value[15] = True
        dcsr_value[2] = True
        yield api.writeGPR(regno=8, value=dcsr_value)
        yield self.execute_progbuf0(api, CSRW_DCSR_S0)
        yield api.writeGPR(regno=8, value=0)
        yield api.readCSR(csr_adr=0x700 | CSRAdr.dcsr)
        self.log("dcsr = {} after CSR progbuf write".format(hex(api.cmd_result())))
        assert api.result[15] and api.result[2], "dcsr progbuf write did not set ebreakm/step"
        yield self.resume_without_running_assert(api)
        yield api.check_halted()
        while not api.halted:
            yield api.check_halted()

        yield self.check_dpc(api, 0x14, "single step halt")
        yield api.readCSR(csr_adr=0x700 | CSRAdr.dcsr)
        assert api.result[9:6] == 4, "step dcsr cause: {} expected 4".format(int(api.result[9:6]))
        yield self.check_gpr(api, regno=8, check_value=0x10000010)

    @block
    def halt_resume_stimulus(
        self,
        dtm_bundle: DmiBundle,
        clock: Any,
        tck: Any = None,
        tms: Any = None,
        tdi: Any = None,
        tdo: Any = None,
    ) -> Any:
        """Stimulus for exercising the debug module through the DMI interface."""

        max_stage_tck = 4000
        progress = {"stage": "created", "time": 0, "tck": 0, "mark_tck": 0, "done": False}

        def mark(stage: str) -> None:
            progress["stage"] = stage
            progress["time"] = now()
            progress["mark_tck"] = progress["tck"]
            self.log("checkpoint: {}".format(stage))

        @instance
        def test() -> Generator[Any, None, None]:
            mark("stimulus started")
            if self.debug_transport == "jtag":
                assert tck is not None and tms is not None and tdi is not None and tdo is not None
                api = JtagDebugAPI(self.config, clock, tck, tms, tdi, tdo, verbose=self.verbose)
                mark("resetting JTAG TAP")
                yield api.reset_tap()
                mark("reading JTAG IDCODE")
                yield api.read_idcode()
                self.log("JTAG IDCODE = {}".format(hex(api.idcode)))
                mark("reading JTAG DTMCS")
                yield api.read_dtmcs()
                self.log("JTAG DTMCS = {}".format(hex(api.dtmcs)))
                self.log("using native JTAG debug transport")
            elif self.debug_transport == "jtagg":
                assert tck is not None and tms is not None and tdi is not None and tdo is not None
                api = Ecp5JtaggDebugAPI(self.config, clock, tck, tms, tdi, tdo, verbose=self.verbose)
                mark("resetting emulated ECP5 TAP")
                yield api.reset_tap()
                self.log("using ECP5 JTAGG debug transport")
            else:
                api = DmiDebugAPI(dtm_bundle=dtm_bundle, clock=clock, config=self.config)
                self.log("using direct DMI debug transport")

            mark("reading debug module version")
            yield api.dmi_read(0x11)
            dmstatus = api.cmd_result()
            dm_version = dmstatus & 0x0F
            self.log("dmstatus = {} version={}".format(hex(dmstatus), dm_version))
            assert dm_version == DEBUG_SPEC_VERSION, "Debug Module version: {} expected {}".format(dm_version, DEBUG_SPEC_VERSION)

            self.log("starting debug module smoke/integration test")
            mark("waiting initial cycles")
            for _ in range(0, 5):
                yield clock.posedge

            mark("checking initial hart state")
            yield api.check_halted()
            assert not api.halted, "Core not in running state"
            self.log("initial hart state: running")

            mark("requesting first halt")
            yield api.halt()
            self.log("halt request acknowledged; hart halted")
            mark("checking first halt dpc")
            yield self.check_dpc(api, 0x0C, "first halt")
            mark("requesting resume")
            yield api.resume()
            self.log("resume request acknowledged; hart running again")
            assert not api.halted, "Core not in running state"
            mark("requesting second halt")
            yield api.halt()
            self.log("second halt successful; entering detailed debug checks")

            mark("checking second halt dpc")
            yield self.check_dpc(api, 0x0C, "second halt")

            gpr_save: list[int] = [0]
            if self.debug_transport in ("jtag", "jtagg"):
                # skip part of test with serial debug transports for performance reasons
                self.log("skipping full GPR save/restore sweep for serial debug transport")
            else:
                self.log("reading architectural GPR state")
                for i in range(1, 32):
                    mark("reading GPR {}".format(abi_name(i)))
                    yield api.readGPR(regno=i)
                    gpr_save.append(api.cmd_result())
                    print("@{}ns [debug-tb]   {:>3} = {}".format(now(), abi_name(i), hex(api.cmd_result())))

                assert gpr_save[10] == 0xFFFFFFFF
                self.log("sanity check: a0 starts at 0xffffffff as expected")

                self.log("testing GPR write path via abstract register access")
                mark("writing GPR ra")
                yield api.writeGPR(regno=1, value=0xDEADBEEF)
                mark("checking GPR ra")
                yield self.check_gpr(api, regno=1, check_value=0xDEADBEEF)

            self.log("testing progbuf0 read/write and postexec path")
            opcode = 0x00100513  # addi a0, zero, 1
            mark("writing progbuf0")
            yield api.writeProgbuf0(opcode)
            mark("reading progbuf0")
            yield api.dmi_read(0x20)
            assert api.cmd_result() == opcode
            self.log("progbuf0 programmed with opcode {}".format(hex(opcode)))
            mark("executing progbuf0")
            yield api.readReg(transfer=False, postexec=True)
            self.log("progbuf execution completed")
            mark("checking progbuf result")
            yield self.check_gpr(api, regno=10, check_value=1)

            if self.config.progbuf_size == 2:
                self.log("testing two-instruction progbuf execution")
                mark("writing two progbuf instructions")
                yield api.dmi_write(0x20, 0x01100513)  # addi a0, zero, 0x11
                yield api.dmi_write(0x21, 0x02200593)  # addi a1, zero, 0x22
                mark("executing two progbuf instructions")
                yield api.readReg(transfer=False, postexec=True)
                mark("checking two progbuf instruction results")
                yield self.check_gpr(api, regno=10, check_value=0x11)
                yield self.check_gpr(api, regno=11, check_value=0x22)

            self.log("testing memory read through progbuf")
            mark("reading memory through progbuf")
            yield api.readMemory(memadr=0x0)
            mem0_save = api.cmd_result()
            self.log("memory[0x0] initial value = {}".format(hex(mem0_save)))
            yield api.readMemory(memadr=0x4)
            self.log("memory[0x4] initial value = {}".format(hex(api.cmd_result())))
            mem_save = api.cmd_result()

            if self.debug_transport in ("jtag", "jtagg"):
                # skip part of test with serial debug transports for performance reasons
                self.log("skipping abstractauto memory sequence for serial debug transport")
            else:
                mark("testing abstractauto memory sequence")
                yield self.check_abstractauto_memory_read(api, mem0_save, mem_save)

            self.log("testing memory write through progbuf")
            mark("writing memory through progbuf")
            yield api.writeMemory(memadr=0x4, memvalue=0xDEADBEEF)
            mark("reading memory after write")
            yield api.readMemory(memadr=0x4)
            self.log("memory[0x4] after write = {}".format(hex(api.cmd_result())))
            self.check_cmd_result(api, 0xDEADBEEF, "memory write check")

            self.log("restoring previous memory value at 0x4")
            mark("restoring memory")
            yield api.writeMemory(memadr=0x4, memvalue=mem_save)
            mark("checking restored memory")
            yield api.readMemory(memadr=0x4)
            self.check_cmd_result(api, mem_save, "memory restore check")

            self.log("reading and modifying dcsr")
            dcsr = 0x700 | CSRAdr.dcsr
            mark("reading dcsr")
            yield api.readCSR(csr_adr=dcsr)
            dcsr_default = api.cmd_result()
            self.log("default dcsr = {}".format(hex(dcsr_default)))
            mark("writing and checking dcsr")
            yield self.set_and_check_dcsr(api, breakm=True, step=True)

            if self.debug_transport in ("jtag", "jtagg"):
                # skip part of test with serial debug transports for performance reasons
                self.log("skipping debug CSR instruction and step/ebreak tests for serial debug transport")
            else:
                mark("testing debug CSR instructions")
                yield self.check_debug_csr_instructions(api)
                yield self.check_debug_csr_abstract_access_rejected(api)
                mark("testing ebreakm and single step")
                yield self.check_ebreakm_and_step(api)

            if self.debug_transport in ("jtag", "jtagg"):
                # skip part of test with serial debug transports for performance reasons
                self.log("setting a0=1 for monitor success path")
                mark("writing GPR a0 for success path")
                yield api.writeGPR(regno=10, value=1)
            else:
                gpr_save[10] = 1
                self.log("restoring all saved GPRs")
                for i in range(1, 32):
                    mark("restoring GPR {}".format(abi_name(i)))
                    yield api.writeGPR(regno=i, value=gpr_save[i])
                    mark("checking restored GPR {}".format(abi_name(i)))
                    yield self.check_gpr(api, regno=i, check_value=gpr_save[i])

            self.log("patching dpc to 0x10 to leave endless loop and hit success path")
            mark("patching dpc to success path")
            yield api.writeCSR(csr_adr=0x700 | CSRAdr.dpc, value=0x10)
            mark("clearing dcsr step and resuming")
            yield self.set_and_check_dcsr(api, breakm=True)
            yield api.resume()
            self.log("final resume issued; program should now reach monitor success write")
            mark("stimulus completed")
            progress["done"] = True

        if self.debug_transport in ("jtag", "jtagg"):
            assert tck is not None

            @instance
            def watchdog() -> Generator[Any, None, None]:
                while True:
                    yield tck.posedge
                    progress["tck"] += 1
                    elapsed_tck = progress["tck"] - progress["mark_tck"]
                    if not progress["done"] and elapsed_tck > max_stage_tck:
                        raise AssertionError(
                            "JTAG debug testbench stalled for {} TCK cycles at stage '{}' "
                            "(last progress @{}ns / TCK {}, current @{}ns / TCK {})".format(
                                elapsed_tck,
                                progress["stage"],
                                progress["time"],
                                progress["mark_tck"],
                                now(),
                                progress["tck"],
                            )
                        )

        return instances()

    @block
    def ndmreset_stimulus(
        self,
        dtm_bundle: DmiBundle,
        clock: Any,
        tck: Any = None,
        tms: Any = None,
        tdi: Any = None,
        tdo: Any = None,
    ) -> Any:
        """Focused stimulus for Debug Module ndmreset behavior."""

        @instance
        def test() -> Generator[Any, None, None]:
            if self.debug_transport == "jtag":
                assert tck is not None and tms is not None and tdi is not None and tdo is not None
                api = JtagDebugAPI(self.config, clock, tck, tms, tdi, tdo, verbose=self.verbose)
                yield api.reset_tap()
                yield api.read_idcode()
                yield api.read_dtmcs()
            elif self.debug_transport == "jtagg":
                assert tck is not None and tms is not None and tdi is not None and tdo is not None
                api = Ecp5JtaggDebugAPI(self.config, clock, tck, tms, tdi, tdo, verbose=self.verbose)
                yield api.reset_tap()
            else:
                api = DmiDebugAPI(dtm_bundle=dtm_bundle, clock=clock, config=self.config)

            for _ in range(0, 5):
                yield clock.posedge

            if not self.config.enableDebugNdmreset:
                c = modbv(0)[32:]
                c[1] = True
                yield api.dmi_write(0x10, c)
                yield api.dmi_read(0x10)
                assert not api.result[1], "dmcontrol.ndmreset should read as 0 when disabled"
                raise StopSimulation

            yield api.halt()

            non_reset_dpc = self.config.reset_address + 0x20
            yield api.writeCSR(csr_adr=0x700 | CSRAdr.dpc, value=non_reset_dpc)
            yield self.check_dpc(api, non_reset_dpc, "patched dpc before ndmreset")

            c = modbv(0)[32:]
            c[1] = True
            yield api.dmi_write(0x10, c)
            for _ in range(0, 4):
                yield clock.posedge
            yield api.dmi_read(0x10)
            assert api.result[1], "dmcontrol.ndmreset did not latch high"

            c[1] = False
            yield api.dmi_write(0x10, c)
            for _ in range(0, 8):
                yield clock.posedge
            yield api.dmi_read(0x10)
            assert not api.result[1], "dmcontrol.ndmreset did not clear"

            yield api.check_halted()
            assert api.halted, "hart did not remain halted after ndmreset"
            yield self.check_dpc(api, self.config.reset_address, "dpc after ndmreset")

            if self.debug_transport == "jtag":
                yield api.read_dtmcs()
                yield api.dmi_read(0x11)
                assert (api.cmd_result() & 0x0F) == DEBUG_SPEC_VERSION, "dmstatus unavailable after JTAG ndmreset"

            raise StopSimulation

        return instances()

    @block
    def testbench(self) -> Any:
        clock = Signal(bool(0))
        reset = ResetSignal(0, active=1, isasync=False)
        system_reset = ResetSignal(0, active=1, isasync=False)

        local_config = self.config
        local_config.enableDebugModule = True
        dtm = DmiBundle(local_config)
        tms = Signal(bool(1))
        tdi = Signal(bool(0))
        tdo = Signal(bool(0))
        tck = Signal(bool(0))
        trstn = Signal(bool(1))

        ram = self.create_ram(self.hexfile, self.ramsize)

        ibus = bonfire_interfaces.DbusBundle(local_config, readOnly=True)
        dbus = bonfire_interfaces.DbusBundle(local_config)
        control = bonfire_interfaces.ControlBundle(local_config)
        debug = bonfire_interfaces.DebugOutputBundle(local_config)

        ram_dbus = bonfire_interfaces.DbusBundle(local_config)
        mon_dbus = bonfire_interfaces.DbusBundle(local_config)
        ram_sel_r = Signal(bool(0))

        mem = sim_ram()
        mem.setLatency(1)

        ibus_if = mem.ram_interface(ram, ibus, clock, system_reset, readOnly=True)
        dbus_if = mem.ram_interface(ram, ram_dbus, clock, system_reset)

        clk_driver = ClkDriver(clock)
        tck_driver = None if self.debug_transport == "jtagg" else ClkDriver(tck, period=73)
        mon_i = monitor_instance(ram, mon_dbus, clock, sigFile=self.sigFile, elfFile=self.elfFile, result=self.monitor_result)
        if self.stimulus_mode == "ndmreset":
            stim = self.ndmreset_stimulus(dtm, clock, tck=tck, tms=tms, tdi=tdi, tdo=tdo)
        elif self.stimulus_mode == "full":
            stim = self.halt_resume_stimulus(dtm, clock, tck=tck, tms=tms, tdi=tdi, tdo=tdo)
        else:
            raise ValueError("Unsupported stimulus_mode: {}".format(self.stimulus_mode))
        jtag_dtm = None
        jtagg_client = None
        jtagg_tap = None
        if self.debug_transport == "jtag":
            jtag_dtm = JtagDTM(local_config).createInstance(clock, reset, tck, tms, tdi, trstn, tdo, dtm)
        elif self.debug_transport == "jtagg":
            jtagg_in = Ecp5JtaggInputBundle()
            jtagg_out = Ecp5JtaggOutputBundle()
            jtagg_client = Ecp5JtaggClient(local_config, clock, reset, jtagg_in, jtagg_out, dtm)
            jtagg_tap = Ecp5JtaggTapEmulator().createInstance(clock, reset, tck, tms, tdi, trstn, tdo, jtagg_in, jtagg_out)
        elif self.debug_transport != "dmi":
            raise ValueError("Unsupported debug_transport: {}".format(self.debug_transport))

        if local_config.enableDebugNdmreset:
            @always_comb
            def system_reset_comb():
                system_reset.next = reset or dtm.ndmreset
        else:
            @always_comb
            def system_reset_comb():
                system_reset.next = reset

        core = bonfire_core_top.BonfireCoreTop(local_config)
        dut = core.createInstance(ibus, dbus, control, clock, system_reset, debug, debugTransportBundle=dtm)

        @always_seq(clock.posedge, reset=system_reset)
        def slave_select():
            if ram_sel_r and ram_dbus.ack_i:
                ram_sel_r.next = False
            elif dbus.en_o and dbus.adr_o >> 2 < self.ramsize:
                ram_sel_r.next = True

        @always_comb
        def slave_connect():
            ram_sel = dbus.adr_o >> 2 < self.ramsize and dbus.en_o
            ram_dbus.en_o.next = ram_sel
            ram_dbus.we_o.next = dbus.we_o
            ram_dbus.adr_o.next = dbus.adr_o[log(self.ramsize, 2) + 2:]
            ram_dbus.db_wr.next = dbus.db_wr

            mon_dbus.en_o.next = not ram_sel and dbus.en_o
            mon_dbus.we_o.next = dbus.we_o
            mon_dbus.adr_o.next = dbus.adr_o
            mon_dbus.db_wr.next = dbus.db_wr

            if ram_sel or ram_sel_r:
                dbus.stall_i.next = ram_dbus.stall_i
                dbus.ack_i.next = ram_dbus.ack_i
                dbus.db_rd.next = ram_dbus.db_rd
            else:
                dbus.stall_i.next = mon_dbus.stall_i
                dbus.ack_i.next = mon_dbus.ack_i
                dbus.db_rd.next = mon_dbus.db_rd

        @always_seq(clock.posedge, reset=system_reset)
        def sim_observe():
            d = core.backend.decode
            if core.backend.execute.taken:
                t_ip = d.debug_current_ip_o
                if self.verbose and d.valid_o and d.debug_word_o[2:0] == 3:
                    instr = int(d.debug_word_o)
                    asm, _ = disassemble(instr)
                    print("@{}ns exc: 0x{:08x}: 0x{:08x} {}".format(now(), int(t_ip), instr, asm))

            inv = d.en_i and d.invalid_opcode and not d.kill_i
            if inv:
                instr = int(d.word_i)
                asm, _ = disassemble(instr)
                assert False, "Invalid opcode @{}: pc:0x{:08x} op:0x{:08x} {} ".format(now(), int(d.current_ip_i), instr, asm)

        return instances()

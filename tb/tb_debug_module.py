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
from rtl.debugModule import AbstractDebugTransportBundle
from rtl.instructions import CSRAdr
from tb.ClkDriver import ClkDriver
from tb.debug_api import DebugAPISim
from tb.disassemble import abi_name
from tb.sim_monitor import monitor_instance
from tb.sim_ram import sim_ram


class BonfireCoreDebugTestbench:
    def __init__(
        self,
        config: config.BonfireConfig = config.BonfireConfig(),
        hexfile: str = "",
        elfFile: str = "",
        sigFile: str = "",
        ramsize: int = 16384,
        verbose: bool = False,
    ) -> None:
        self.config = config
        self.hexfile = hexfile
        self.elfFile = elfFile
        self.sigFile = sigFile
        self.ramsize = ramsize
        self.verbose = verbose

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

    def check_cmd_result(self, api: DebugAPISim, check_value: int, text: str = "") -> None:
        assert api.cmd_result() == check_value, "{} result: {} expected: {}".format(text, hex(api.cmd_result()), hex(check_value))
        self.log("{} -> {}".format(text or "cmd result", hex(api.cmd_result())))

    def check_gpr(self, api: DebugAPISim, regno: int, check_value: int) -> Generator[Any, None, None]:
        yield api.readGPR(regno=regno)
        assert api.cmd_result() == check_value, "check_gpr failure result: {} expected: {}".format(hex(api.cmd_result()), hex(check_value))
        self.log("verify GPR {} = {}".format(abi_name(regno), hex(api.cmd_result())))

    def set_and_check_dcsr(self, api: DebugAPISim, breakm: bool = False, step: bool = False) -> Generator[Any, None, None]:
        dcsr = 0x700 | CSRAdr.dcsr
        v = modbv(0)[32:]
        v[15] = breakm
        v[2] = step
        yield api.writeReg(regno=dcsr, value=v)
        yield api.readReg(regno=dcsr)
        self.log("dcsr = {} (ebreakm={}, step={})".format(hex(api.cmd_result()), breakm, step))
        assert api.result[15] == breakm and api.result[2] == step, "dcsr write failed"

    @block
    def halt_resume_stimulus(self, dtm_bundle: AbstractDebugTransportBundle, clock: Any) -> Any:
        """Stimulus for exercising the debug module through the DMI interface."""

        @instance
        def test() -> Generator[Any, None, None]:
            api = DebugAPISim(dtm_bundle=dtm_bundle, clock=clock)

            self.log("starting debug module smoke/integration test")
            for _ in range(0, 5):
                yield clock.posedge

            yield api.check_halted()
            assert not api.halted, "Core not in running state"
            self.log("initial hart state: running")

            yield api.halt()
            self.log("halt request acknowledged; hart halted")
            yield api.resume()
            self.log("resume request acknowledged; hart running again")
            assert not api.halted, "Core not in running state"
            yield api.halt()
            self.log("second halt successful; entering detailed debug checks")

            yield api.readReg(regno=0x700 | CSRAdr.dpc)
            self.log("initial dpc = {}".format(hex(api.cmd_result())))

            gpr_save: list[int] = [0]
            self.log("reading architectural GPR state")
            for i in range(1, 32):
                yield api.readGPR(regno=i)
                gpr_save.append(api.cmd_result())
                print("@{}ns [debug-tb]   {:>3} = {}".format(now(), abi_name(i), hex(api.cmd_result())))

            assert gpr_save[10] == 0xFFFFFFFF
            self.log("sanity check: a0 starts at 0xffffffff as expected")

            self.log("testing GPR write path via abstract register access")
            yield api.writeGPR(regno=1, value=0xDEADBEEF)
            yield self.check_gpr(api, regno=1, check_value=0xDEADBEEF)

            self.log("testing progbuf0 read/write and postexec path")
            opcode = 0x00100513
            yield api.dmi_write(0x20, opcode)
            yield api.dmi_read(0x20)
            assert api.cmd_result() == opcode
            self.log("progbuf0 programmed with opcode {}".format(hex(opcode)))
            yield api.readReg(transfer=False, postexec=True)
            self.log("progbuf execution completed")
            yield self.check_gpr(api, regno=10, check_value=1)

            self.log("testing memory read through progbuf")
            yield api.readMemory(memadr=0x4)
            self.log("memory[0x4] initial value = {}".format(hex(api.cmd_result())))
            mem_save = api.cmd_result()

            self.log("testing memory write through progbuf")
            yield api.writeMemory(memadr=0x4, memvalue=0xDEADBEEF)
            yield api.readMemory(memadr=0x4)
            self.log("memory[0x4] after write = {}".format(hex(api.cmd_result())))
            self.check_cmd_result(api, 0xDEADBEEF, "memory write check")

            self.log("restoring previous memory value at 0x4")
            yield api.writeMemory(memadr=0x4, memvalue=mem_save)
            yield api.readMemory(memadr=0x4)
            self.check_cmd_result(api, mem_save, "memory restore check")

            self.log("reading and modifying dcsr")
            dcsr = 0x700 | CSRAdr.dcsr
            yield api.readReg(regno=dcsr)
            dcsr_default = api.cmd_result()
            self.log("default dcsr = {}".format(hex(dcsr_default)))
            yield self.set_and_check_dcsr(api, breakm=True, step=True)

            gpr_save[10] = 1
            self.log("restoring all saved GPRs")
            for i in range(1, 32):
                yield api.writeGPR(regno=i, value=gpr_save[i])
                yield self.check_gpr(api, regno=i, check_value=gpr_save[i])

            self.log("patching dpc to 0x10 to leave endless loop and hit success path")
            yield api.writeReg(regno=0x700 | CSRAdr.dpc, value=0x10)
            yield self.set_and_check_dcsr(api, breakm=True)
            yield api.resume()
            self.log("final resume issued; program should now reach monitor success write")

        return instances()

    @block
    def testbench(self) -> Any:
        clock = Signal(bool(0))
        reset = ResetSignal(0, active=1, isasync=False)

        local_config = self.config
        local_config.enableDebugModule = True
        dtm = AbstractDebugTransportBundle(local_config)

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

        ibus_if = mem.ram_interface(ram, ibus, clock, reset, readOnly=True)
        dbus_if = mem.ram_interface(ram, ram_dbus, clock, reset)

        clk_driver = ClkDriver(clock)
        mon_i = monitor_instance(ram, mon_dbus, clock, sigFile=self.sigFile, elfFile=self.elfFile)
        stim = self.halt_resume_stimulus(dtm, clock)

        core = bonfire_core_top.BonfireCoreTop(local_config)
        dut = core.createInstance(ibus, dbus, control, clock, reset, debug, debugTransportBundle=dtm)

        @always_seq(clock.posedge, reset=reset)
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

        @always_seq(clock.posedge, reset=reset)
        def sim_observe():
            d = core.backend.decode
            if core.backend.execute.taken:
                t_ip = d.debug_current_ip_o
                if self.verbose:
                    print("@{}ns exc: {} : {} ".format(now(), t_ip, d.debug_word_o))

            inv = d.en_i and d.invalid_opcode and not d.kill_i
            assert not inv, "Invalid opcode @{}: pc:{} op:{} ".format(now(), d.current_ip_i, d.word_i)

        return instances()

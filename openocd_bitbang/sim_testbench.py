"""
Bonfire Core OpenOCD remote_bitbang simulation testbench.
(c) 2026 The Bonfire Project
License: See LICENSE
"""
from __future__ import annotations

import socket
from math import log
from threading import Event
from typing import Any

from myhdl import *

from openocd_bitbang.remote_bitbang import remote_bitbang_server
from rtl import bonfire_core_top, bonfire_interfaces, config
from rtl.debugModule import AbstractDebugTransportBundle, t_abstractCommandState
from rtl.jtag_dtm import JtagDTM, t_tapState
from tb.ClkDriver import ClkDriver
from tb.sim_ram import sim_ram


def _format_scan_bits(bits: list[int]) -> str:
    if not bits:
        return "bits=0"

    value = sum(bit << index for index, bit in enumerate(bits))
    lsb_first = "".join(str(bit) for bit in bits)
    if len(bits) <= 64:
        return "bits={} lsb_first={} value=0x{:x}".format(len(bits), lsb_first, value)

    low32 = value & 0xFFFFFFFF
    return "bits={} low32=0x{:08x} lsb_first_head={}...tail={}".format(
        len(bits),
        low32,
        lsb_first[:64],
        lsb_first[-16:],
    )


class OpenOCDBitbangTestbench:
    def __init__(
        self,
        config: config.BonfireConfig = config.BonfireConfig(),
        hexfile: str = "",
        ramsize: int = 16384,
        server_socket: socket.socket | None = None,
        ready_event: Event | None = None,
        stop_event: Event | None = None,
        verbose: bool = False,
        observe_jtag: bool = False,
        debug_trace: bool = False,
        exit_on_client_quit: bool = False,
    ) -> None:
        self.config = config
        self.hexfile = hexfile
        self.ramsize = ramsize
        self.server_socket = server_socket
        self.ready_event = ready_event
        self.stop_event = stop_event
        self.verbose = verbose
        self.observe_jtag = observe_jtag
        self.debug_trace = debug_trace
        self.exit_on_client_quit = exit_on_client_quit

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

    @block
    def jtag_observer(self, clock: Any, tck: Any, tms: Any, tdi: Any, tdo: Any, tap_state: Any) -> Any:
        @instance
        def observe() -> Any:
            last_state = tap_state.val
            last_tck = bool(tck)
            scan_kind = ""
            tdi_bits: list[int] = []
            tdo_bits: list[int] = []

            while True:
                yield clock.posedge
                yield delay(0)

                if not self.observe_jtag:
                    last_state = tap_state.val
                    last_tck = bool(tck)
                    continue

                current_state = tap_state.val
                current_tck = bool(tck)
                tck_rise = current_tck and not last_tck

                if current_state != last_state:
                    if last_state == t_tapState.shift_ir or last_state == t_tapState.shift_dr:
                        print(
                            "@{} [jtag-observer] end {} scan: TDI {} TDO {}".format(
                                now(),
                                scan_kind,
                                _format_scan_bits(tdi_bits),
                                _format_scan_bits(tdo_bits),
                            ),
                            flush=True,
                        )
                        scan_kind = ""
                        tdi_bits = []
                        tdo_bits = []

                    print(
                        "@{} [jtag-observer] state {} -> {} (tck={} tms={} tdi={} tdo={})".format(
                            now(),
                            last_state,
                            current_state,
                            int(current_tck),
                            int(tms),
                            int(tdi),
                            int(tdo),
                        ),
                        flush=True,
                    )

                    if current_state == t_tapState.shift_ir:
                        scan_kind = "IR"
                        print("@{} [jtag-observer] begin IR scan".format(now()), flush=True)
                    elif current_state == t_tapState.shift_dr:
                        scan_kind = "DR"
                        print("@{} [jtag-observer] begin DR scan".format(now()), flush=True)

                if tck_rise and (current_state == t_tapState.shift_ir or current_state == t_tapState.shift_dr):
                    tdi_bits.append(int(tdi))
                    tdo_bits.append(int(tdo))

                last_state = current_state
                last_tck = current_tck

        return instances()

    @block
    def debug_trace_monitor(self, clock: Any, dtm: Any, core: Any) -> Any:
        debug_regs = core.debugRegs
        assert debug_regs is not None

        trace_history: list[str] = []
        trace_history_limit = 96

        def append_trace(message: str) -> None:
            line = "@{} [openocd-debug] {}".format(now(), message)
            trace_history.append(line)
            if len(trace_history) > trace_history_limit:
                trace_history.pop(0)
            if self.debug_trace:
                print(line, flush=True)

        def dump_trace(reason: str) -> None:
            print("@{} [openocd-debug] trace dump: {}".format(now(), reason), flush=True)
            for line in trace_history:
                print(line, flush=True)

        def command_word_summary(command_word: int) -> str:
            command_type = (command_word >> 24) & 0xFF
            command_name = "access_reg" if command_type == 0 else "type_{}".format(command_type)
            return (
                "cmd type={} aarsize={} write={} transfer={} postexec={} regno=0x{:x}"
            ).format(
                command_name,
                (command_word >> 20) & 0x7,
                (command_word >> 16) & 0x1,
                (command_word >> 17) & 0x1,
                (command_word >> 18) & 0x1,
                command_word & 0xFFFF,
            )

        def command_summary() -> str:
            return (
                "cmd type={} aarsize={} write={} transfer={} postexec={} regno=0x{:x} "
                "data0=0x{:08x} dpc=0x{:08x}"
            ).format(
                debug_regs.commandType,
                int(debug_regs.aarsize),
                int(debug_regs.write),
                int(debug_regs.transfer),
                int(debug_regs.postexec),
                int(debug_regs.regno),
                int(debug_regs.dataRegs[0]),
                int(debug_regs.dpc) << self.config.ip_low,
            )

        def progbuf_summary() -> str:
            return "progbuf0=0x{:08x} progbuf1=0x{:08x}".format(
                int(debug_regs.progbuf0),
                int(debug_regs.progbuf1),
            )

        @instance
        def monitor() -> Any:
            last_state = debug_regs.abstractCommandState.val
            last_hart_state = debug_regs.hartState.val
            last_progbuf0 = int(debug_regs.progbuf0)
            last_progbuf1 = int(debug_regs.progbuf1)
            trace_dumped = False

            while True:
                yield clock.posedge
                yield delay(0)

                decode = core.backend.decode
                state = debug_regs.abstractCommandState.val
                hart_state = debug_regs.hartState.val
                progbuf0 = int(debug_regs.progbuf0)
                progbuf1 = int(debug_regs.progbuf1)

                if hart_state != last_hart_state:
                    append_trace("hart {} -> {} dpc=0x{:08x}".format(last_hart_state, hart_state, int(debug_regs.dpc) << self.config.ip_low))

                if progbuf0 != last_progbuf0:
                    append_trace("progbuf0 <= 0x{:08x}".format(progbuf0))
                if progbuf1 != last_progbuf1:
                    append_trace("progbuf1 <= 0x{:08x}".format(progbuf1))

                if dtm.en:
                    if dtm.we:
                        append_trace("DMI write adr=0x{:02x} data=0x{:08x}".format(int(dtm.adr), int(dtm.dbi)))
                        if int(dtm.adr) == 0x17:
                            append_trace(
                                "abstract command write: {} data0=0x{:08x} {}".format(
                                    command_word_summary(int(dtm.dbi)),
                                    int(debug_regs.dataRegs[0]),
                                    progbuf_summary(),
                                )
                            )
                    else:
                        # OpenOCD polls dmstatus heavily while idle. Suppress the
                        # all-zero idle reads so relevant progbuf/DMI traffic stays visible.
                        if not (int(dtm.adr) == 0x11 and int(dtm.dbo) == 0):
                            append_trace("DMI read adr=0x{:02x} data=0x{:08x}".format(int(dtm.adr), int(dtm.dbo)))

                if state != last_state:
                    append_trace("abstract state {} -> {}".format(last_state, state))

                    if last_state == t_abstractCommandState.taken and (
                        state == t_abstractCommandState.exec or state == t_abstractCommandState.regvalid
                    ):
                        if debug_regs.postexec:
                            append_trace("Command Start: {} {}".format(command_summary(), progbuf_summary()))
                        else:
                            append_trace("Command Start: {}".format(command_summary()))

                    if last_state == t_abstractCommandState.exec and state == t_abstractCommandState.wait_retire:
                        append_trace(
                            "Progbuf Exec slot=0 pc=0x{:08x} instr=0x{:08x}".format(
                                int(decode.debug_current_ip_o),
                                int(debug_regs.progbuf0),
                            )
                        )
                    elif last_state == t_abstractCommandState.exec2 and state == t_abstractCommandState.wait_retire:
                        append_trace(
                            "Progbuf Exec slot=1 pc=0x{:08x} instr=0x{:08x}".format(
                                int(decode.debug_current_ip_o),
                                int(debug_regs.progbuf1),
                            )
                        )

                    if state == t_abstractCommandState.none:
                        append_trace(
                            "Command Finish: data0=0x{:08x} cmderr={} dpc=0x{:08x}".format(
                                int(debug_regs.dataRegs[0]),
                                int(debug_regs.cmderr),
                                int(debug_regs.dpc) << self.config.ip_low,
                            )
                        )

                inv = decode.en_i and decode.invalid_opcode and not decode.kill_i
                if inv and not trace_dumped:
                    trace_dumped = True
                    dump_trace(
                        "invalid opcode pc=0x{:08x} op=0x{:08x} current_ip=0x{:08x}".format(
                            int(decode.current_ip_i),
                            int(decode.word_i),
                            int(decode.debug_current_ip_o),
                        )
                    )
                    raise AssertionError(
                        "Invalid opcode @{}: pc:{:08x} op:{:08x}".format(
                            now(),
                            int(decode.current_ip_i),
                            int(decode.word_i),
                        )
                    )

                last_state = state
                last_hart_state = hart_state
                last_progbuf0 = progbuf0
                last_progbuf1 = progbuf1

        return instances()

    @block
    def testbench(self, enableJTAGObserver:bool=False) -> Any:
        assert self.server_socket is not None

        clock = Signal(bool(0))
        reset = ResetSignal(0, active=1, isasync=False)
        tck = Signal(bool(0))
        trstn = Signal(bool(1))
        tms = Signal(bool(1))
        tdi = Signal(bool(0))
        tdo = Signal(bool(0))
        tap_state = Signal(t_tapState.test_logic_reset)

        local_config = self.config
        local_config.enableDebugModule = True
        dtm = AbstractDebugTransportBundle(local_config)
        ram = self.create_ram(self.hexfile, self.ramsize)

        ibus = bonfire_interfaces.DbusBundle(local_config, readOnly=True)
        dbus = bonfire_interfaces.DbusBundle(local_config)
        control = bonfire_interfaces.ControlBundle(local_config)
        debug = bonfire_interfaces.DebugOutputBundle(local_config)

        ram_dbus = bonfire_interfaces.DbusBundle(local_config)
        ram_sel_r = Signal(bool(0))

        mem = sim_ram()
        mem.setLatency(1)

        ibus_if = mem.ram_interface(ram, ibus, clock, reset, readOnly=True)
        dbus_if = mem.ram_interface(ram, ram_dbus, clock, reset)

        clk_driver = ClkDriver(clock, period=10)
        jtag_dtm = JtagDTM(local_config).createInstance(clock, reset, tck, tms, tdi, trstn, tdo, dtm, tap_state_o=tap_state)
        bitbang = remote_bitbang_server(
            clock,
            tck,
            tms,
            tdi,
            trstn,
            tdo,
            self.server_socket,
            verbose=self.verbose,
            client_quit_event=self.stop_event if self.exit_on_client_quit else None,
        )
        if enableJTAGObserver:
            observer = self.jtag_observer(clock, tck, tms, tdi, tdo, tap_state)

        core = bonfire_core_top.BonfireCoreTop(local_config)
        dut = core.createInstance(ibus, dbus, control, clock, reset, debug, debugTransportBundle=dtm)
        debug_trace_i = self.debug_trace_monitor(clock, dtm, core)

        if self.ready_event is not None:
            self.ready_event.set()

        @always_seq(clock.posedge, reset=reset)
        def slave_select() -> None:
            if ram_sel_r and ram_dbus.ack_i:
                ram_sel_r.next = False
            elif dbus.en_o and dbus.adr_o >> 2 < self.ramsize:
                ram_sel_r.next = True

        @always_comb
        def slave_connect() -> None:
            ram_sel = dbus.en_o and dbus.adr_o >> 2 < self.ramsize
            ram_dbus.en_o.next = ram_sel
            ram_dbus.we_o.next = dbus.we_o
            ram_dbus.adr_o.next = dbus.adr_o[log(self.ramsize, 2) + 2:]
            ram_dbus.db_wr.next = dbus.db_wr

            dbus.stall_i.next = ram_dbus.stall_i
            dbus.ack_i.next = ram_dbus.ack_i
            dbus.db_rd.next = ram_dbus.db_rd

        @always_seq(clock.posedge, reset=reset)
        def sim_observe() -> None:
            pass

        @instance
        def stop_monitor() -> Any:
            try:
                while True:
                    if self.stop_event is not None and self.stop_event.is_set():
                        raise StopSimulation
                    yield clock.posedge
            finally:
                try:
                    self.server_socket.close()
                except Exception:
                    pass

        return instances()

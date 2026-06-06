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
from rtl.debugModule import AbstractDebugTransportBundle
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
            d = core.backend.decode
            inv = d.en_i and d.invalid_opcode and not d.kill_i
            assert not inv, "Invalid opcode @{}: pc:{} op:{} ".format(now(), d.current_ip_i, d.word_i)

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


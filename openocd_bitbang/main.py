"""
Bonfire OpenOCD remote_bitbang simulation server runner.
(c) 2026 The Bonfire Project
License: See LICENSE
"""

from __future__ import annotations

import argparse
import socket
import threading
from dataclasses import dataclass, field
from pathlib import Path
from threading import Event
from typing import Any

from myhdl import *

from rtl.config import BonfireConfig
from rtl.debugModule import AbstractDebugTransportBundle
from rtl.jtag_dtm import JtagDTM, t_tapState
from tb.ClkDriver import ClkDriver
from openocd_bitbang.remote_bitbang import remote_bitbang_server

DEFAULT_OPENOCD_BITBANG_PORT = 3335


@dataclass
class OpenOCDBitbangControl:
    host: str = "127.0.0.1"
    port: int = DEFAULT_OPENOCD_BITBANG_PORT
    ready_event: Event = field(default_factory=Event)
    stop_event: Event = field(default_factory=Event)


def _bind_server_socket(host: str, port: int) -> socket.socket:
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(1)
    return server_socket


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


@block
def openocd_bitbang_testbench(
    control: OpenOCDBitbangControl,
    verbose: bool = False,
    observe_jtag: bool = False,
    exit_on_client_quit: bool = False,
) -> Any:
    conf = BonfireConfig()
    clock = Signal(bool(0))
    reset = ResetSignal(0, active=1, isasync=False)
    tck = Signal(bool(0))
    trstn = Signal(bool(1))
    tms = Signal(bool(1))
    tdi = Signal(bool(0))
    tdo = Signal(bool(0))
    tap_state = Signal(t_tapState.test_logic_reset)
    dtm = AbstractDebugTransportBundle(conf)

    server_socket = _bind_server_socket(control.host, control.port)
    control.port = server_socket.getsockname()[1]
    control.ready_event.set()
    print("OpenOCD remote_bitbang listening on {}:{}".format(control.host, control.port), flush=True)

    clk_driver = ClkDriver(clock, period=10)
    dut = JtagDTM(conf).createInstance(clock, reset, tck, tms, tdi, trstn, tdo, dtm, tap_state_o=tap_state)
    bitbang = remote_bitbang_server(
        clock,
        tck,
        tms,
        tdi,
        trstn,
        tdo,
        server_socket,
        verbose=verbose,
        client_quit_event=control.stop_event if exit_on_client_quit else None,
    )

    @instance
    def jtag_observer() -> Any:
        last_state = tap_state.val
        last_tck = bool(tck)
        scan_kind = ""
        tdi_bits: list[int] = []
        tdo_bits: list[int] = []

        while True:
            yield clock.posedge
            yield delay(0)

            if not observe_jtag:
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

    @instance
    def stop_monitor() -> Any:
        try:
            while True:
                if control.stop_event.is_set():
                    raise StopSimulation
                yield clock.posedge
        finally:
            try:
                server_socket.close()
            except Exception:
                pass

    return instances()


def serve_openocd_bitbang(
    host: str = "127.0.0.1",
    port: int = DEFAULT_OPENOCD_BITBANG_PORT,
    verbose: bool = False,
    vcd: Path | None = None,
    observe_jtag: bool = False,
    exit_on_client_quit: bool = False,
) -> int:
    control = OpenOCDBitbangControl(host=host, port=port)
    tb = openocd_bitbang_testbench(
        control,
        verbose=verbose,
        observe_jtag=observe_jtag,
        exit_on_client_quit=exit_on_client_quit,
    )
    sim_error: list[BaseException] = []

    def run_server() -> None:
        try:
            tb.config_sim(trace=vcd is not None, filename=str(vcd) if vcd is not None else None)
            tb.run_sim()
        except BaseException as exc:  # pragma: no cover - surfaced in main thread
            sim_error.append(exc)
        finally:
            try:
                tb.quit_sim()
            except Exception:
                pass

    thread = threading.Thread(target=run_server, name="openocd-bitbang-sim", daemon=True)
    thread.start()

    try:
        if not control.ready_event.wait(timeout=5.0):
            raise RuntimeError("OpenOCD remote_bitbang server did not become ready in time")

        while thread.is_alive():
            thread.join(timeout=0.2)
    except KeyboardInterrupt:
        print("Stopping OpenOCD remote_bitbang server...", flush=True)
        control.stop_event.set()
        thread.join(timeout=5.0)
    finally:
        control.stop_event.set()

    if thread.is_alive():
        raise RuntimeError("OpenOCD remote_bitbang simulation thread did not stop cleanly")

    if sim_error:
        raise sim_error[0]

    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Bonfire OpenOCD remote_bitbang simulation server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=DEFAULT_OPENOCD_BITBANG_PORT, help="TCP port to bind (default: 3335)")
    parser.add_argument("--verbose", action="store_true", help="Print remote_bitbang protocol activity")
    parser.add_argument("--observe-jtag", action="store_true", help="Print decoded TAP state and scan activity")
    parser.add_argument("--exit-on-client-quit", action="store_true", help="Exit after the remote_bitbang client sends Q")
    parser.add_argument("--vcd", type=Path, default=None, help="Optional VCD output filename base")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    return serve_openocd_bitbang(
        host=args.host,
        port=args.port,
        verbose=args.verbose,
        vcd=args.vcd,
        observe_jtag=args.observe_jtag,
        exit_on_client_quit=args.exit_on_client_quit,
    )


if __name__ == "__main__":
    raise SystemExit(main())

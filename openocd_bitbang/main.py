"""
Bonfire Core OpenOCD remote_bitbang simulation server runner.
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

from openocd_bitbang.sim_testbench import OpenOCDBitbangTestbench
from rtl.config import BonfireConfig

DEFAULT_OPENOCD_BITBANG_PORT = 3335
DEFAULT_HEX_PATH = Path("code/build/debug-tests/endless.hex")


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


def serve_openocd_bitbang(
    hexfile: Path,
    host: str = "127.0.0.1",
    port: int = DEFAULT_OPENOCD_BITBANG_PORT,
    ramsize: int = 16384,
    verbose: bool = False,
    vcd: Path | None = None,
    observe_jtag: bool = False,
    debug_trace: bool = False,
    info_trace: bool = False,
    enable_ndmreset: bool = True,
    exit_on_client_quit: bool = False,
) -> int:
    control = OpenOCDBitbangControl(host=host, port=port)
    server_socket = _bind_server_socket(control.host, control.port)
    control.port = server_socket.getsockname()[1]
    print("OpenOCD remote_bitbang listening on {}:{}".format(control.host, control.port), flush=True)

    bonfire_config = BonfireConfig()
    bonfire_config.enableDebugNdmreset = enable_ndmreset

    tb = OpenOCDBitbangTestbench(
        bonfire_config,
        hexfile=str(hexfile),
        ramsize=ramsize,
        server_socket=server_socket,
        ready_event=control.ready_event,
        stop_event=control.stop_event,
        verbose=verbose,
        observe_jtag=observe_jtag,
        debug_trace=debug_trace,
        info_trace=info_trace,
        exit_on_client_quit=exit_on_client_quit,
    ).testbench()
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

    thread = threading.Thread(target=run_server, name="openocd-bitbang-core-sim", daemon=True)
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
    parser = argparse.ArgumentParser(description="Run the Bonfire Core OpenOCD remote_bitbang simulation server")
    parser.add_argument("--hex", type=Path, default=DEFAULT_HEX_PATH, help="HEX image to load")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=DEFAULT_OPENOCD_BITBANG_PORT, help="TCP port to bind (default: 3335)")
    parser.add_argument("--ramsize", type=int, default=16384, help="RAM size in 32-bit words")
    parser.add_argument("--verbose", action="store_true", help="Print remote_bitbang protocol activity")
    parser.add_argument("--observe-jtag", action="store_true", help="Print decoded TAP state and scan activity")
    parser.add_argument("--debug-trace", action="store_true", help="Print Debug Module and progbuf execution trace")
    parser.add_argument("--info-trace", action="store_true", help="Print compact hart and abstract-command trace")
    parser.add_argument("--disable-ndmreset", action="store_true", help="Disable Debug Module ndmreset handling")
    parser.add_argument("--exit-on-client-quit", action="store_true", help="Exit after the remote_bitbang client sends Q")
    parser.add_argument("--vcd", type=Path, default=None, help="Optional VCD output filename base")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    hexfile = args.hex
    if not hexfile.is_absolute():
        hexfile = Path.cwd() / hexfile
    if not hexfile.is_file():
        raise FileNotFoundError("OpenOCD bitbang HEX file not found: {}".format(hexfile))
    return serve_openocd_bitbang(
        hexfile=hexfile,
        host=args.host,
        port=args.port,
        ramsize=args.ramsize,
        verbose=args.verbose,
        vcd=args.vcd,
        observe_jtag=args.observe_jtag,
        debug_trace=args.debug_trace,
        info_trace=args.info_trace,
        enable_ndmreset=not args.disable_ndmreset,
        exit_on_client_quit=args.exit_on_client_quit,
    )


if __name__ == "__main__":
    raise SystemExit(main())

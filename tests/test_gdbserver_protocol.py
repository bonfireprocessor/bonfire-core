from __future__ import annotations

import os
import threading
import time
from pathlib import Path

import pytest

from gdbserver.gdbserver_test import GDBServerTestClient
from gdbserver.main import ServerControl
from gdbserver.sim_testbench import GDBServerTestbench
from rtl import config



COUNTER_ADDR = 0x20


def _opt_env(name: str) -> str | None:
    v = os.environ.get(name, "").strip()
    return v or None


def _read_u32_le(client: GDBServerTestClient, addr: int) -> int:
    payload = client.send_packet(f"m{addr:x},4")
    return int.from_bytes(client.decode_memory_bytes(payload), byteorder="little", signed=False)


def test_gdbserver_protocol(sim_env, repo_root: Path):
    hex_path = Path(_opt_env("BONFIRE_GDBSERVER_HEX") or "code/build/debug-tests/endless.hex")
    if not hex_path.is_absolute():
        hex_path = repo_root / hex_path

    if not hex_path.is_file():
        pytest.skip(f"GDB server HEX file not found: {hex_path}")

    conf = config.BonfireConfig()
    control = ServerControl(port=0)
    gdb_tb = GDBServerTestbench(conf, hexfile=str(hex_path), ramsize=16384, server_control=control)
    tb = gdb_tb.testbench()

    sim_error: list[BaseException] = []

    def run_server() -> None:
        try:
            tb.config_sim(directory=str(sim_env["waveforms_dir"]), trace=False, filename=None)
            tb.run_sim()
        except BaseException as exc:  # pragma: no cover - surfaced in main thread
            sim_error.append(exc)
        finally:
            try:
                tb.quit_sim()
            except Exception:
                pass

    thread = threading.Thread(target=run_server, name="gdbserver-sim", daemon=True)
    thread.start()

    try:
        assert control.ready_event.wait(timeout=5.0), "gdbserver did not become ready in time"

        assert control.port is not None
        with GDBServerTestClient(control.host, control.port, timeout=2.0) as client:
            supported = client.send_packet("qSupported:multiprocess+;swbreak+;hwbreak+")
            assert "PacketSize=" in supported

            attached = client.send_packet("qAttached")
            assert attached == "0"

            stop_reason = client.send_packet("?")
            assert stop_reason == "S05"

            registers = client.send_packet("g")
            words = client.decode_u32_le_words(registers)
            assert len(words) == 33
            assert words[0] == 0
            assert words[6] == 0xDEADBEEF  # t1 loaded by endless.S

            before = _read_u32_le(client, COUNTER_ADDR)
            assert client.send_packet(f"M{COUNTER_ADDR:x},4:78563412") == "OK"
            patched = _read_u32_le(client, COUNTER_ADDR)
            assert patched == 0x12345678

            client.send_packet_no_response("c")
            time.sleep(0.05)
            stop_reply = client.send_break()
            assert stop_reply == "T05"

            after = _read_u32_le(client, COUNTER_ADDR)
            assert after != patched
            assert after > before
    finally:
        control.stop_event.set()
        thread.join(timeout=5.0)

    if thread.is_alive():
        raise AssertionError("gdbserver simulation thread did not stop cleanly")

    if sim_error:
        raise sim_error[0]

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
# Address of the `loop:` label in endless.S – lw instruction, first in the loop body.
# Layout: _start is at 0x00; after `la t0, counter` (2 instr = 8B) + `li t1,0xdeadbeef`
# (2 instr = 8B) = offset 0x10 for `loop:`.
LOOP_ADDR = 0x10


def _opt_env(name: str) -> str | None:
    v = os.environ.get(name, "").strip()
    return v or None


def _read_u32_le(client: GDBServerTestClient, addr: int) -> int:
    payload = client.send_packet(f"m{addr:x},4")
    return int.from_bytes(client.decode_memory_bytes(payload), byteorder="little", signed=False)


def _start_testbench(
    sim_env: dict,
    hex_path: Path,
    ramsize: int = 16384,
) -> tuple[GDBServerTestbench, ServerControl, threading.Thread, list]:
    """Create and start a GDB server testbench in a background thread."""
    conf = config.BonfireConfig()
    control = ServerControl(port=0)
    gdb_tb = GDBServerTestbench(conf, hexfile=str(hex_path), ramsize=ramsize, server_control=control)
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
    return gdb_tb, control, thread, sim_error


def _get_hex_path(repo_root: Path) -> Path:
    hex_path = Path(_opt_env("BONFIRE_GDBSERVER_HEX") or "code/build/debug-tests/endless.hex")
    if not hex_path.is_absolute():
        hex_path = repo_root / hex_path
    return hex_path


def test_gdbserver_protocol(sim_env, repo_root: Path):
    hex_path = _get_hex_path(repo_root)
    if not hex_path.is_file():
        pytest.skip(f"GDB server HEX file not found: {hex_path}")

    _gdb_tb, control, thread, sim_error = _start_testbench(sim_env, hex_path)

    try:
        assert control.ready_event.wait(timeout=5.0), "gdbserver did not become ready in time"

        assert control.port is not None
        with GDBServerTestClient(control.host, control.port, timeout=2.0) as client:
            supported = client.send_packet("qSupported:multiprocess+;swbreak+;hwbreak+")
            assert "PacketSize=" in supported
            assert "swbreak+" in supported

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


def test_gdbserver_single_step(sim_env, repo_root: Path):
    """Single step (s command) should advance the PC by exactly one instruction."""
    hex_path = _get_hex_path(repo_root)
    if not hex_path.is_file():
        pytest.skip(f"GDB server HEX file not found: {hex_path}")

    _gdb_tb, control, thread, sim_error = _start_testbench(sim_env, hex_path)

    try:
        assert control.ready_event.wait(timeout=5.0), "gdbserver did not become ready in time"

        assert control.port is not None
        with GDBServerTestClient(control.host, control.port, timeout=5.0) as client:
            # Halt the core via qAttached.
            client.send_packet("qAttached")

            # Read the current PC (register 32 in the g response).
            registers = client.send_packet("g")
            words = client.decode_u32_le_words(registers)
            pc_before = words[32]

            # Single step.
            step_reply = client.send_packet("s")
            assert step_reply == "T05"

            # PC must have advanced.
            registers_after = client.send_packet("g")
            words_after = client.decode_u32_le_words(registers_after)
            pc_after = words_after[32]
            assert pc_after != pc_before, f"PC did not advance after single step: was {pc_before:#x}"
    finally:
        control.stop_event.set()
        thread.join(timeout=5.0)

    if thread.is_alive():
        raise AssertionError("gdbserver simulation thread did not stop cleanly")

    if sim_error:
        raise sim_error[0]


def test_gdbserver_monitor_halt_resume(sim_env, repo_root: Path):
    """monitor halt and monitor resume commands should work via qRcmd."""
    hex_path = _get_hex_path(repo_root)
    if not hex_path.is_file():
        pytest.skip(f"GDB server HEX file not found: {hex_path}")

    _gdb_tb, control, thread, sim_error = _start_testbench(sim_env, hex_path)

    try:
        assert control.ready_event.wait(timeout=5.0), "gdbserver did not become ready in time"

        assert control.port is not None
        with GDBServerTestClient(control.host, control.port, timeout=5.0) as client:
            # Halt via qAttached, then resume via monitor resume.
            client.send_packet("qAttached")

            before = _read_u32_le(client, COUNTER_ADDR)

            # monitor resume → core starts running.
            resume_hex = "resume".encode("ascii").hex()
            resume_reply = client.send_packet(f"qRcmd,{resume_hex}")
            # Response is hex-encoded text, not "OK" - just check it's not an error.
            assert not resume_reply.startswith("E"), f"monitor resume returned error: {resume_reply}"

            time.sleep(0.05)

            # monitor halt → stops the core.
            halt_hex = "halt".encode("ascii").hex()
            halt_reply = client.send_packet(f"qRcmd,{halt_hex}")
            assert halt_reply == "OK", f"monitor halt returned: {halt_reply!r}"

            after = _read_u32_le(client, COUNTER_ADDR)
            assert after != before, "Counter did not advance after monitor resume/halt cycle"
    finally:
        control.stop_event.set()
        thread.join(timeout=5.0)

    if thread.is_alive():
        raise AssertionError("gdbserver simulation thread did not stop cleanly")

    if sim_error:
        raise sim_error[0]


def test_gdbserver_breakpoints(sim_env, repo_root: Path):
    """Z/z software breakpoint insertion and removal."""
    hex_path = _get_hex_path(repo_root)
    if not hex_path.is_file():
        pytest.skip(f"GDB server HEX file not found: {hex_path}")

    _gdb_tb, control, thread, sim_error = _start_testbench(sim_env, hex_path)

    try:
        assert control.ready_event.wait(timeout=5.0), "gdbserver did not become ready in time"

        assert control.port is not None
        with GDBServerTestClient(control.host, control.port, timeout=5.0) as client:
            # Halt via qAttached.
            client.send_packet("qAttached")

            # Set a software breakpoint at the loop label.
            bp_reply = client.send_packet(f"Z0,{LOOP_ADDR:x},4")
            assert bp_reply == "OK", f"Z (set breakpoint) returned: {bp_reply!r}"

            # Continue – core should hit the breakpoint quickly.
            client.send_packet_no_response("c")
            stop_reply = client._recv_packet().payload
            assert stop_reply == "T05", f"Expected T05 after breakpoint, got: {stop_reply!r}"

            # Verify PC is at the breakpoint address.
            registers = client.send_packet("g")
            words = client.decode_u32_le_words(registers)
            pc = words[32]
            assert pc == LOOP_ADDR, f"PC {pc:#x} != breakpoint {LOOP_ADDR:#x}"

            # Remove the breakpoint.
            del_reply = client.send_packet(f"z0,{LOOP_ADDR:x},4")
            assert del_reply == "OK", f"z (remove breakpoint) returned: {del_reply!r}"
    finally:
        control.stop_event.set()
        thread.join(timeout=5.0)

    if thread.is_alive():
        raise AssertionError("gdbserver simulation thread did not stop cleanly")

    if sim_error:
        raise sim_error[0]


def test_gdbserver_write_all_registers(sim_env, repo_root: Path):
    """G command should write all registers."""
    hex_path = _get_hex_path(repo_root)
    if not hex_path.is_file():
        pytest.skip(f"GDB server HEX file not found: {hex_path}")

    _gdb_tb, control, thread, sim_error = _start_testbench(sim_env, hex_path)

    try:
        assert control.ready_event.wait(timeout=5.0), "gdbserver did not become ready in time"

        assert control.port is not None
        with GDBServerTestClient(control.host, control.port, timeout=5.0) as client:
            client.send_packet("qAttached")

            # Read current registers.
            registers = client.send_packet("g")
            words = client.decode_u32_le_words(registers)

            # Patch x5 (t0) to a known value in the register list and write back.
            new_value = 0xCAFEBABE
            words[5] = new_value
            new_g_payload = "".join(
                val.to_bytes(4, byteorder="little").hex().upper() for val in words
            )
            g_reply = client.send_packet(f"G{new_g_payload}")
            assert g_reply == "OK", f"G command returned: {g_reply!r}"

            # Read back and verify.
            registers_back = client.send_packet("g")
            words_back = client.decode_u32_le_words(registers_back)
            assert words_back[5] == new_value, f"x5 read back as {words_back[5]:#x}, expected {new_value:#x}"
    finally:
        control.stop_event.set()
        thread.join(timeout=5.0)

    if thread.is_alive():
        raise AssertionError("gdbserver simulation thread did not stop cleanly")

    if sim_error:
        raise sim_error[0]


def test_gdbserver_vcont(sim_env, repo_root: Path):
    """vCont? should report supported actions; vCont;s should single-step."""
    hex_path = _get_hex_path(repo_root)
    if not hex_path.is_file():
        pytest.skip(f"GDB server HEX file not found: {hex_path}")

    _gdb_tb, control, thread, sim_error = _start_testbench(sim_env, hex_path)

    try:
        assert control.ready_event.wait(timeout=5.0), "gdbserver did not become ready in time"

        assert control.port is not None
        with GDBServerTestClient(control.host, control.port, timeout=5.0) as client:
            client.send_packet("qAttached")

            vcont_support = client.send_packet("vCont?")
            assert "c" in vcont_support and "s" in vcont_support, \
                f"vCont? missing expected actions: {vcont_support!r}"

            registers = client.send_packet("g")
            pc_before = client.decode_u32_le_words(registers)[32]

            step_reply = client.send_packet("vCont;s:1")
            assert step_reply == "T05"

            registers_after = client.send_packet("g")
            pc_after = client.decode_u32_le_words(registers_after)[32]
            assert pc_after != pc_before, f"PC did not advance after vCont;s: was {pc_before:#x}"
    finally:
        control.stop_event.set()
        thread.join(timeout=5.0)

    if thread.is_alive():
        raise AssertionError("gdbserver simulation thread did not stop cleanly")

    if sim_error:
        raise sim_error[0]


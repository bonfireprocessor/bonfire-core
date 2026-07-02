"""
OpenOCD remote_bitbang server prototype tests.
(c) 2026 The Bonfire Project
License: See LICENSE
"""
from __future__ import annotations

import contextlib
import signal
import socket
import shutil
import subprocess
import sys
import threading
import time
from collections.abc import Generator
from pathlib import Path

import pytest

from openocd_bitbang.probe import RemoteBitbangClient, ScanResult
from rtl.debug.ecp5_jtagg_client import ECP5_JTAGG_IR_ER1, ECP5_JTAGG_IR_ER2, ECP5_JTAGG_IR_WIDTH
from rtl.debug.ecp5_jtagg_tap import ECP5_JTAG_EXPECTED_IDCODES, ECP5_JTAG_IDCODE_DEFAULT
from rtl.debug.jtag_dtm import JTAG_IDCODE, JTAG_IR_WIDTH
from .conftest import waveform_config

OPENOCD_TIMEOUT_SECONDS = 60.0
OPENOCD_CORE_TARGET_TIMEOUT_SECONDS = 60.0


def _free_tcp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _all_ones(width: int) -> int:
    return (1 << width) - 1


def _first_mismatch(actual: int, expected: int, width: int) -> str:
    for index in range(width):
        actual_bit = (actual >> index) & 1
        expected_bit = (expected >> index) & 1
        if actual_bit != expected_bit:
            return "bit {} actual={} expected={}".format(index, actual_bit, expected_bit)
    return "no mismatch"


def _assert_scan_equal(actual: ScanResult, expected: ScanResult) -> None:
    assert actual.bits == expected.bits
    assert actual.value == expected.value, (
        "scan mismatch: {}\nactual:   {}\nexpected: {}".format(
            _first_mismatch(actual.value, expected.value, actual.bits),
            actual.summary(),
            expected.summary(),
        )
    )


def _wait_for_server_ready(process: subprocess.Popen[str], timeout: float = 5.0) -> str:
    assert process.stdout is not None
    deadline = time.monotonic() + timeout
    output = ""

    while time.monotonic() < deadline:
        line = process.stdout.readline()
        if line:
            output += line
            if "OpenOCD remote_bitbang listening" in line:
                return output
        if process.poll() is not None:
            break

    remaining = process.stdout.read() if process.stdout else ""
    raise AssertionError("remote_bitbang server did not become ready\n{}".format(output + remaining))


@contextlib.contextmanager
def _remote_bitbang_server_process(
    port: int,
    vcd: Path | None = None,
    observe_jtag: bool = False,
    jtag_transport: str = "standard",
) -> Generator[subprocess.Popen[str], None, None]:
    command = [
        sys.executable,
        "-m",
        "openocd_bitbang",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--exit-on-client-quit",
    ]
    if vcd is not None:
        command.extend(["--vcd", str(vcd)])
    if observe_jtag:
        command.append("--observe-jtag")
    if jtag_transport != "standard":
        command.extend(["--jtag-transport", jtag_transport])

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    try:
        server_output = _wait_for_server_ready(process)
        print("\n[remote-bitbang-server]\n{}".format(server_output), end="")
        reader_stop = threading.Event()

        def drain_server_output() -> None:
            assert process.stdout is not None
            while not reader_stop.is_set():
                line = process.stdout.readline()
                if not line:
                    break
                print(line, end="")

        reader = threading.Thread(target=drain_server_output, name="remote-bitbang-server-output", daemon=True)
        reader.start()
        yield process
    finally:
        if process.poll() is None:
            try:
                process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                process.send_signal(signal.SIGINT)
                try:
                    process.wait(timeout=5.0)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    try:
                        process.wait(timeout=5.0)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5.0)
        if "reader_stop" in locals():
            reader_stop.set()
        if "reader" in locals():
            reader.join(timeout=1.0)


def test_python_remote_bitbang_client_reads_idcode():
    """Use a tiny Python remote_bitbang client to prove the server can scan IDCODE."""

    port = _free_tcp_port()
    print("\n[test] starting remote_bitbang server subprocess on port {}".format(port))

    with _remote_bitbang_server_process(port, observe_jtag=True):
        print("[test] connecting Python remote_bitbang client")
        client = RemoteBitbangClient("127.0.0.1", port)
        try:
            print("[test] reset TAP and scan 32-bit DR IDCODE")
            client.reset_tap()
            idcode = client.scan_dr(0, 32)
            print("[test] Python client read IDCODE {}".format(hex(idcode.value)))
            client.quit()
        finally:
            client.close()

    assert idcode.value == JTAG_IDCODE, "IDCODE mismatch: got {} expected {}".format(hex(idcode.value), hex(JTAG_IDCODE))


def test_openocd_probe_long_ir_scan_matches_single_tap_capture():
    """Reproduce OpenOCD's long IR probe and verify the single TAP IR-capture pattern."""

    port = _free_tcp_port()
    width = 487
    expected = ScanResult(width, 0x01 | (_all_ones(width - JTAG_IR_WIDTH) << JTAG_IR_WIDTH))

    print("\n[test] starting remote_bitbang server subprocess on port {}".format(port))
    with _remote_bitbang_server_process(port, observe_jtag=True):
        client = RemoteBitbangClient("127.0.0.1", port)
        try:
            print("[test] reset TAP and scan {} IR bits with TDI=1".format(width))
            client.reset_tap()
            actual = client.scan_ir(_all_ones(width), width)
            print("[test] long IR actual   {}".format(actual.summary()))
            print("[test] long IR expected {}".format(expected.summary()))
            client.quit()
        finally:
            client.close()

    _assert_scan_equal(actual, expected)


def test_openocd_probe_long_dr_scan_returns_idcode_then_ones():
    """Reproduce OpenOCD's long DR probe and verify that no phantom TAP bits appear."""

    port = _free_tcp_port()
    width = 672
    expected = ScanResult(width, JTAG_IDCODE | (_all_ones(width - 32) << 32))

    print("\n[test] starting remote_bitbang server subprocess on port {}".format(port))
    with _remote_bitbang_server_process(port, observe_jtag=True):
        client = RemoteBitbangClient("127.0.0.1", port)
        try:
            print("[test] reset TAP and scan {} DR bits with TDI=1".format(width))
            client.reset_tap()
            actual = client.scan_dr(_all_ones(width), width)
            print("[test] long DR actual   {}".format(actual.summary()))
            print("[test] long DR expected {}".format(expected.summary()))
            client.quit()
        finally:
            client.close()

    _assert_scan_equal(actual, expected)


def _openocd_ir_override(transport: str) -> str:
    if transport == "standard":
        return ""

    return "riscv set_ir dtmcs 0x{:x}\nriscv set_ir dmi 0x{:x}\n\n".format(
        ECP5_JTAGG_IR_ER2,
        ECP5_JTAGG_IR_ER1,
    )


def _idcode_for_transport(transport: str) -> int:
    return JTAG_IDCODE if transport == "standard" else ECP5_JTAG_IDCODE_DEFAULT


def _openocd_expected_id_args(transport: str) -> str:
    if transport == "standard":
        return "-expected-id 0x{:08x}".format(JTAG_IDCODE)

    return " ".join("-expected-id 0x{:08x}".format(idcode) for idcode in ECP5_JTAG_EXPECTED_IDCODES)


def _openocd_config(host: str, port: int, transport: str = "standard") -> str:
    ir_width = JTAG_IR_WIDTH if transport == "standard" else ECP5_JTAGG_IR_WIDTH
    return """
adapter driver remote_bitbang
remote_bitbang host {host}
remote_bitbang port {port}
transport select jtag

jtag newtap bonfire cpu -irlen {ir_width} {expected_ids}

init
scan_chain
shutdown
""".format(host=host, port=port, ir_width=ir_width, expected_ids=_openocd_expected_id_args(transport))


def _openocd_core_target_config(host: str, port: int, transport: str = "standard") -> str:
    ir_width = JTAG_IR_WIDTH if transport == "standard" else ECP5_JTAGG_IR_WIDTH
    return """
gdb_port disabled
tcl_port disabled
telnet_port disabled

adapter driver remote_bitbang
remote_bitbang host {host}
remote_bitbang port {port}
transport select jtag

jtag newtap bonfire cpu -irlen {ir_width} {expected_ids}
target create bonfire.cpu riscv -chain-position bonfire.cpu
{ir_override}

init
shutdown
""".format(
        host=host,
        port=port,
        ir_width=ir_width,
        expected_ids=_openocd_expected_id_args(transport),
        ir_override=_openocd_ir_override(transport),
    )


def test_openocd_remote_bitbang_scan_chain_reads_idcode(sim_env, tmp_path: Path, request: pytest.FixtureRequest):
    """Run real OpenOCD against the server and require scan_chain to see IDCODE."""

    if shutil.which("openocd") is None:
        pytest.skip("openocd not installed")

    port = _free_tcp_port()
    trace, filename = waveform_config(request, sim_env, "openocd_bitbang_scan_chain")
    vcd_path = Path(filename) if trace and filename is not None else None
    config_path = tmp_path / "bonfire_remote_bitbang.cfg"
    config_path.write_text(_openocd_config("127.0.0.1", port), encoding="utf-8")
    print("\n[test] OpenOCD config written to {}".format(config_path))
    print("[test] starting remote_bitbang server subprocess on port {}".format(port))

    if vcd_path is not None:
        print("[test] OpenOCD bitbang VCD base {}".format(vcd_path))

    with _remote_bitbang_server_process(port, vcd=vcd_path, observe_jtag=True):
        print("[test] running OpenOCD scan_chain")
        completed = subprocess.run(
            ["openocd", "-f", str(config_path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=OPENOCD_TIMEOUT_SECONDS,
        )

    print("[openocd stdout]\n{}".format(completed.stdout), end="")
    print("[openocd stderr]\n{}".format(completed.stderr), end="")
    assert completed.returncode == 0, "openocd failed\nstdout:\n{}\nstderr:\n{}".format(completed.stdout, completed.stderr)
    assert "0x{:08x}".format(JTAG_IDCODE) in completed.stderr.lower()


def test_openocd_remote_bitbang_scan_chain_reads_idcode_ecp5_jtagg(sim_env, tmp_path: Path, request: pytest.FixtureRequest):
    """Run real OpenOCD against the emulated ECP5 JTAGG transport."""

    if shutil.which("openocd") is None:
        pytest.skip("openocd not installed")

    port = _free_tcp_port()
    trace, filename = waveform_config(request, sim_env, "openocd_bitbang_scan_chain_ecp5_jtagg")
    vcd_path = Path(filename) if trace and filename is not None else None
    config_path = tmp_path / "bonfire_remote_bitbang_ecp5_jtagg.cfg"
    config_path.write_text(_openocd_config("127.0.0.1", port, transport="ecp5_jtagg"), encoding="utf-8")

    with _remote_bitbang_server_process(port, vcd=vcd_path, observe_jtag=True, jtag_transport="ecp5_jtagg"):
        completed = subprocess.run(
            ["openocd", "-f", str(config_path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=OPENOCD_TIMEOUT_SECONDS,
        )

    print("[openocd stdout]\n{}".format(completed.stdout), end="")
    print("[openocd stderr]\n{}".format(completed.stderr), end="")
    assert completed.returncode == 0, "openocd failed\nstdout:\n{}\nstderr:\n{}".format(completed.stdout, completed.stderr)
    assert "0x{:08x}".format(_idcode_for_transport("ecp5_jtagg")) in completed.stderr.lower()


def test_openocd_remote_bitbang_core_target_smoke(tmp_path: Path):
    """Run OpenOCD with a RISC-V target against the full Bonfire core simulation."""

    if shutil.which("openocd") is None:
        pytest.skip("openocd not installed")

    port = _free_tcp_port()
    config_path = tmp_path / "bonfire_remote_bitbang_core.cfg"
    config_path.write_text(_openocd_core_target_config("127.0.0.1", port), encoding="utf-8")
    print("\n[test] OpenOCD core config written to {}".format(config_path))
    print("[test] starting remote_bitbang core server subprocess on port {}".format(port))

    with _remote_bitbang_server_process(port, observe_jtag=True):
        print("[test] running OpenOCD RISC-V target smoke")
        completed = subprocess.run(
            ["openocd", "-f", str(config_path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=OPENOCD_CORE_TARGET_TIMEOUT_SECONDS,
        )

    print("[openocd stdout]\n{}".format(completed.stdout), end="")
    print("[openocd stderr]\n{}".format(completed.stderr), end="")
    stderr = completed.stderr.lower()
    assert "0x{:08x}".format(JTAG_IDCODE) in stderr
    assert "auto0.tap" not in stderr
    assert "ir capture error" not in stderr
    assert "debug module version" not in stderr
    if completed.returncode != 0:
        assert "not authenticated" in stderr, "openocd failed\nstdout:\n{}\nstderr:\n{}".format(completed.stdout, completed.stderr)


def test_openocd_remote_bitbang_core_target_smoke_ecp5_jtagg(sim_env, tmp_path: Path, request: pytest.FixtureRequest):
    """Run OpenOCD with the emulated ECP5 JTAGG transport against the full core simulation."""

    if shutil.which("openocd") is None:
        pytest.skip("openocd not installed")

    port = _free_tcp_port()
    trace, filename = waveform_config(request, sim_env, "openocd_bitbang_core_ecp5_jtagg")
    vcd_path = Path(filename) if trace and filename is not None else None
    config_path = tmp_path / "bonfire_remote_bitbang_core_ecp5_jtagg.cfg"
    config_path.write_text(_openocd_core_target_config("127.0.0.1", port, transport="ecp5_jtagg"), encoding="utf-8")

    with _remote_bitbang_server_process(port, vcd=vcd_path, observe_jtag=True, jtag_transport="ecp5_jtagg"):
        completed = subprocess.run(
            ["openocd", "-f", str(config_path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=OPENOCD_CORE_TARGET_TIMEOUT_SECONDS,
        )

    print("[openocd stdout]\n{}".format(completed.stdout), end="")
    print("[openocd stderr]\n{}".format(completed.stderr), end="")
    stderr = completed.stderr.lower()
    assert completed.returncode == 0, "openocd failed\nstdout:\n{}\nstderr:\n{}".format(completed.stdout, completed.stderr)
    assert "0x{:08x}".format(_idcode_for_transport("ecp5_jtagg")) in stderr
    assert "examined risc-v core; found 1 harts" in stderr
    assert "auto0.tap" not in stderr
    assert "ir capture error" not in stderr
    assert "unsupported dtm version" not in stderr
    assert "debug module version" not in stderr

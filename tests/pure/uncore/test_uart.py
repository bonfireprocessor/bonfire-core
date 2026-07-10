from __future__ import annotations

from tb.uncore.uart import tb_uart

from tests.conftest import run_sim, waveform_config


def test_uart_registers(request, sim_env):
    trace, filename = waveform_config(request, sim_env, "uart_registers")
    run_sim(
        tb_uart.tb_uart_registers(),
        trace=trace,
        filename=filename,
        waveforms_dir=sim_env["waveforms_dir"],
        duration=5000,
    )


def test_uart_tx_capture(request, sim_env):
    trace, filename = waveform_config(request, sim_env, "uart_tx_capture")
    run_sim(
        tb_uart.tb_uart_tx_capture(),
        trace=trace,
        filename=filename,
        waveforms_dir=sim_env["waveforms_dir"],
        duration=20000,
    )


def test_uart_rx(request, sim_env):
    trace, filename = waveform_config(request, sim_env, "uart_rx")
    run_sim(
        tb_uart.tb_uart_rx(),
        trace=trace,
        filename=filename,
        waveforms_dir=sim_env["waveforms_dir"],
        duration=10000,
    )

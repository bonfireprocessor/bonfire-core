from __future__ import annotations

from myhdl import ResetSignal, Signal, StopSimulation, block, delay, instance, instances, modbv

from rtl import config
from rtl.bonfire_interfaces import DbusBundle
from rtl.uncore.uart import BonfireUart
from tb.ClkDriver import ClkDriver
from tb.uncore.uart.uart_capture import UartCaptureResult, uart_tx_capture


CLK_PERIOD = 10
UART_REG_DATA = 0x00
UART_REG_STATUS_CONTROL = 0x04
UART_REG_EXT_CONTROL = 0x08
UART_REG_INTERRUPT = 0x0C

UART_STATUS_RX_READY = 0x00000001
UART_STATUS_TX_READY = 0x00000002
UART_STATUS_TX_IN_PROGRESS = 0x00000004

UART_CONTROL_ENABLE = 0x00010000
UART_CONTROL_EXT_MODE = 0x00020000
UART_IRQ_TX_ENABLE = 0x00000002
UART_IRQ_RX_ENABLE = 0x00000001
UART_IRQ_TX_PENDING = 0x00020000
UART_IRQ_RX_PENDING = 0x00010000
UART_STOP_MARK = 0x1A


def _dbus_signals():
    conf = config.BonfireConfig()
    dbus = DbusBundle(conf)
    clock = Signal(bool(0))
    reset = ResetSignal(0, active=1, isasync=False)
    tx = Signal(bool(1))
    rx = Signal(bool(1))
    irq = Signal(bool(0))
    enabled = Signal(bool(0))
    return dbus, clock, reset, tx, rx, irq, enabled


def _drive_idle(dbus):
    dbus.en_o.next = False
    dbus.we_o.next = 0
    dbus.adr_o.next = 0
    dbus.db_wr.next = 0


def _print_reg_read(name, value):
    print("{} read: 0x{:08X}".format(name, value))


def _print_reg_write(name, value):
    print("{} write: 0x{:08X}".format(name, value))


@block
def tb_uart_registers():
    dbus, clock, reset, tx, rx, irq, enabled = _dbus_signals()

    clk_driver = ClkDriver(clock, period=CLK_PERIOD)
    uart = BonfireUart(fifo_bits=5)
    dut = uart.createInstance(dbus, clock, reset, tx, rx, irq, enabled)

    @instance
    def stimulus():
        _drive_idle(dbus)
        reset.next = True
        yield clock.posedge
        reset.next = False
        yield clock.posedge

        def write_reg(address, data, we=0xF):
            _print_reg_write("UART[0x{:02X}]".format(address), data)
            dbus.adr_o.next = address
            dbus.db_wr.next = modbv(data)[32:]
            dbus.we_o.next = we
            dbus.en_o.next = True
            yield delay(1)
            assert dbus.ack_i
            yield clock.posedge
            _drive_idle(dbus)
            yield clock.posedge

        def read_reg(address, target):
            dbus.adr_o.next = address
            dbus.we_o.next = 0
            dbus.en_o.next = True
            yield delay(1)
            assert dbus.ack_i
            target[0] = int(dbus.db_rd)
            _print_reg_read("UART[0x{:02X}]".format(address), target[0])
            yield clock.posedge
            _drive_idle(dbus)
            yield clock.posedge

        value = [0]

        print("UART register test: reset/status")
        yield read_reg(UART_REG_STATUS_CONTROL, value)
        assert value[0] & UART_STATUS_RX_READY == 0
        assert value[0] & UART_STATUS_TX_READY == UART_STATUS_TX_READY
        assert value[0] & UART_STATUS_TX_IN_PROGRESS == 0
        assert not enabled

        print("UART register test: status writes are ignored")
        yield write_reg(UART_REG_STATUS_CONTROL, UART_CONTROL_ENABLE | 0x0007)
        yield read_reg(UART_REG_EXT_CONTROL, value)
        assert value[0] & UART_CONTROL_ENABLE == 0
        assert value[0] & 0x0000FFFF == 0xFFFF
        assert not enabled

        print("UART register test: extended control")
        ext_control = UART_CONTROL_EXT_MODE | UART_CONTROL_ENABLE | 0x00030000 | 0x0014
        yield write_reg(UART_REG_EXT_CONTROL, ext_control)
        yield read_reg(UART_REG_EXT_CONTROL, value)
        assert value[0] & 0x0003FFFF == ext_control & 0x0003FFFF
        yield read_reg(UART_REG_STATUS_CONTROL, value)
        assert (value[0] >> 16) & 0xF == 5

        print("UART register test: interrupt register")
        yield write_reg(UART_REG_INTERRUPT, UART_IRQ_TX_ENABLE)
        yield read_reg(UART_REG_INTERRUPT, value)
        assert value[0] & UART_IRQ_TX_ENABLE == UART_IRQ_TX_ENABLE
        assert value[0] & UART_IRQ_TX_PENDING == UART_IRQ_TX_PENDING
        assert irq
        print("UART register test finished")

        raise StopSimulation

    return instances()


@block
def tb_uart_tx_capture():
    dbus, clock, reset, tx, rx, irq, enabled = _dbus_signals()
    stop = Signal(bool(0))
    saw_in_progress = Signal(bool(0))
    result = UartCaptureResult()
    expected_text = "The quick brown fox"
    critical_patterns = [0x00, 0xFF, 0x55, 0x01, 0xFE]
    expected = [ord(ch) for ch in expected_text] + critical_patterns + [UART_STOP_MARK]
    divisor = 3
    bit_time = (divisor + 1) * CLK_PERIOD

    clk_driver = ClkDriver(clock, period=CLK_PERIOD)
    uart = BonfireUart(fifo_bits=5)
    dut = uart.createInstance(dbus, clock, reset, tx, rx, irq, enabled)
    capture = uart_tx_capture(
        tx,
        bit_time,
        result,
        stop,
        stop_mark=UART_STOP_MARK,
        echo_output=False,
        expected_signature=expected,
    )

    @instance
    def stimulus():
        _drive_idle(dbus)
        reset.next = True
        yield clock.posedge
        reset.next = False
        yield clock.posedge

        def write_reg(address, data):
            _print_reg_write("UART[0x{:02X}]".format(address), data)
            dbus.adr_o.next = address
            dbus.db_wr.next = modbv(data)[32:]
            dbus.we_o.next = 0xF
            dbus.en_o.next = True
            yield delay(1)
            assert dbus.ack_i
            yield clock.posedge
            _drive_idle(dbus)
            yield clock.posedge

        def read_status(target):
            dbus.adr_o.next = UART_REG_STATUS_CONTROL
            dbus.we_o.next = 0
            dbus.en_o.next = True
            yield delay(1)
            target[0] = int(dbus.db_rd)
            yield clock.posedge
            _drive_idle(dbus)
            yield clock.posedge

        print("UART TX capture test: bit_time={} ns divisor={}".format(bit_time, divisor))
        yield write_reg(UART_REG_EXT_CONTROL, divisor | UART_CONTROL_ENABLE | UART_CONTROL_EXT_MODE)

        status = [0]
        for byte in expected:
            print("UART TX stimulus byte: 0x{:02X}".format(byte))
            timeout = 0
            yield read_status(status)
            while (status[0] & UART_STATUS_TX_READY) == 0:
                yield read_status(status)
                timeout += 1
                assert timeout < 200
            _print_reg_read("UART status before TX write", status[0])

            yield write_reg(UART_REG_DATA, byte)
            yield read_status(status)
            _print_reg_read("UART status after TX write", status[0])
            if status[0] & UART_STATUS_TX_IN_PROGRESS:
                saw_in_progress.next = True

        while not stop:
            yield read_status(status)
            if status[0] & UART_STATUS_TX_IN_PROGRESS:
                saw_in_progress.next = True

    @instance
    def checker():
        while not stop:
            yield clock.posedge

        assert saw_in_progress
        assert result.framing_errors == 0
        assert result.total_count == len(expected)
        assert result.bytes == expected
        assert result.text == expected_text + "\\0x00\\0xFFU\\0x01\\0xFE\\0x1A"
        assert result.signature_ok is True
        print("UART capture bytes: {}".format(" ".join("0x{:02X}".format(b) for b in result.bytes)))
        print("UART capture string: {}".format(result.text))
        print("UART capture total_count: {}".format(result.total_count))
        print("UART capture framing_errors: {}".format(result.framing_errors))
        print("UART capture signature_ok: {}".format(result.signature_ok))
        raise StopSimulation

    return instances()


@block
def tb_uart_rx():
    dbus, clock, reset, tx, rx, irq, enabled = _dbus_signals()
    expected = [0x55, 0x00, 0xFF, 0xA5]
    divisor = 3
    bit_time = (divisor + 1) * CLK_PERIOD

    clk_driver = ClkDriver(clock, period=CLK_PERIOD)
    uart = BonfireUart(fifo_bits=5)
    dut = uart.createInstance(dbus, clock, reset, tx, rx, irq, enabled)

    @instance
    def stimulus():
        _drive_idle(dbus)
        rx.next = True
        reset.next = True
        yield clock.posedge
        reset.next = False
        yield clock.posedge

        def write_reg(address, data):
            _print_reg_write("UART[0x{:02X}]".format(address), data)
            dbus.adr_o.next = address
            dbus.db_wr.next = modbv(data)[32:]
            dbus.we_o.next = 0xF
            dbus.en_o.next = True
            yield delay(1)
            assert dbus.ack_i
            yield clock.posedge
            _drive_idle(dbus)
            yield clock.posedge

        def read_reg(address, target):
            dbus.adr_o.next = address
            dbus.we_o.next = 0
            dbus.en_o.next = True
            yield delay(1)
            assert dbus.ack_i
            target[0] = int(dbus.db_rd)
            _print_reg_read("UART[0x{:02X}]".format(address), target[0])
            yield clock.posedge
            _drive_idle(dbus)
            yield clock.posedge

        def send_rx_byte(byte):
            print("UART RX stimulus byte: 0x{:02X}".format(byte))
            rx.next = False
            yield delay(bit_time)
            for bit in range(8):
                rx.next = bool((byte >> bit) & 1)
                yield delay(bit_time)
            rx.next = True
            yield delay(bit_time)

        print("UART RX test: bit_time={} ns divisor={}".format(bit_time, divisor))
        yield write_reg(UART_REG_EXT_CONTROL, divisor | UART_CONTROL_ENABLE | UART_CONTROL_EXT_MODE)
        yield write_reg(UART_REG_INTERRUPT, UART_IRQ_RX_ENABLE)

        status = [0]
        data = [0]
        received = []
        for byte in expected:
            yield send_rx_byte(byte)

            timeout = 0
            yield read_reg(UART_REG_STATUS_CONTROL, status)
            while (status[0] & UART_STATUS_RX_READY) == 0:
                yield read_reg(UART_REG_STATUS_CONTROL, status)
                timeout += 1
                assert timeout < 50

            assert status[0] & UART_STATUS_RX_READY
            yield read_reg(UART_REG_INTERRUPT, data)
            assert data[0] & UART_IRQ_RX_ENABLE
            assert data[0] & UART_IRQ_RX_PENDING
            assert irq

            yield read_reg(UART_REG_DATA, data)
            received.append(data[0] & 0xFF)
            assert data[0] & 0x80000000 == 0

            yield read_reg(UART_REG_STATUS_CONTROL, status)
            assert status[0] & UART_STATUS_RX_READY == 0

        assert received == expected
        print("UART RX received bytes: {}".format(" ".join("0x{:02X}".format(b) for b in received)))
        raise StopSimulation

    return instances()

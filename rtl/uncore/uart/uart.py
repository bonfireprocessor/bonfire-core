"""
Bonfire DBus UART with zpuino-uart compatible registers.

This is intentionally smaller than the original zpuino UART.  The first
implementation provides the register surface, a divisor driven 8N1 TX path, and
a one-byte RX holding register.  RX FIFO support is intentionally deferred.

DBus register interface
=======================

The UART is mapped as four word-aligned 32-bit registers.  DBus address bits
``adr_o[4:2]`` select the register, so the visible byte offsets are compatible
with the zpuino UART register map:

| Offset | Read                         | Write                       |
| ------ | ---------------------------- | --------------------------- |
| 0x00   | Receive register             | Transmit register           |
| 0x04   | Status register              | Ignored                     |
| 0x08   | Extended control register    | Extended control register   |
| 0x0c   | Interrupt register           | Interrupt register          |

Transmit register, offset 0x00
------------------------------

| Bits  | Description                                                       |
| ----- | ----------------------------------------------------------------- |
| 7:0   | Byte to transmit.  Accepted when the one-byte TX buffer is free. |

Receive register, offset 0x00
-----------------------------

| Bits  | Description                                                       |
| ----- | ----------------------------------------------------------------- |
| 7:0   | Last received byte.  A read clears RX ready.                      |
| 31    | Framing error flag for the byte, valid in extended mode.          |

Status register, offset 0x04
----------------------------

| Bits  | Description                                                       |
| ----- | ----------------------------------------------------------------- |
| 0     | RX ready.  Set when the RX holding register contains a byte.      |
| 1     | TX ready.  Set when the TX buffer can accept a byte.              |
| 2     | TX in progress.  Set while an 8N1 frame is being shifted out.     |
| 3     | RX FIFO nearly full.  Always zero until RX FIFO is implemented.   |
| 19:16 | ``fifo_bits`` when extended mode is enabled, otherwise zero.      |

Extended control register, offset 0x08
--------------------------------------

| Bits  | Description                                                       |
| ----- | ----------------------------------------------------------------- |
| 15:0  | TX bit divisor.                                                   |
| 16    | UART enable bit, exposed on the ``enabled`` output.               |
| 17    | Extended mode enable.                                             |
| 31:18 | FIFO threshold field.  Only ``fifo_bits`` low bits are stored.    |

Interrupt register, offset 0x0c
-------------------------------

| Bits  | Description                                                       |
| ----- | ----------------------------------------------------------------- |
| 0     | RX interrupt enable.                                              |
| 1     | TX interrupt enable.                                              |
| 3     | RX FIFO nearly-full interrupt enable.                             |
| 16    | RX interrupt pending.  Level based: ``rx_int_en and rx_ready``.   |
| 17    | TX interrupt pending.  Level based: ``tx_int_en and tx_ready``.   |
| 19    | FIFO interrupt pending.  Always zero until RX FIFO is implemented. |
"""

from __future__ import annotations

from typing import Any

from myhdl import Signal, always_comb, always_seq, block, instances, modbv

from rtl.bonfire_interfaces import DbusBundle
from rtl.type_aliases import BitSignal


class BonfireUart:
    def __init__(self, fifo_bits: int = 5) -> None:
        assert fifo_bits > 0 and fifo_bits <= 14, "fifo_bits must fit in extended control bits"
        self.fifo_bits = fifo_bits

    @block
    def registers(
        self,
        dbus: DbusBundle,
        clock: BitSignal,
        reset: BitSignal,
        irq: BitSignal,
        enabled: BitSignal,
        tx_divider: Any,
        ext_mode_en: Any,
        enabled_q: Any,
        fifo_threshold: Any,
        tx_busy: Any,
        tx_buffer_valid: Any,
        tx_reg_write: Any,
        tx_reg_write_data: Any,
        rx_data: Any,
        rx_ready: Any,
        rx_framing_error: Any,
        rx_reg_read: Any,
    ) -> Any:
        rx_int_en = Signal(bool(0))
        tx_int_en = Signal(bool(0))
        fifo_int_en = Signal(bool(0))

        tx_ready = Signal(bool(1))
        rx_pending = Signal(bool(0))
        tx_pending = Signal(bool(0))
        write_cycle = Signal(bool(0))
        read_data = Signal(modbv(0)[32:])

        @always_comb
        def status_signals():
            tx_ready.next = not tx_buffer_valid
            rx_pending.next = rx_int_en and rx_ready
            tx_pending.next = tx_int_en and tx_ready

        @always_comb
        def outputs():
            enabled.next = enabled_q
            irq.next = rx_pending or tx_pending
            dbus.ack_i.next = dbus.en_o
            dbus.stall_i.next = False
            dbus.error_i.next = False
            dbus.db_rd.next = read_data
            write_cycle.next = dbus.en_o and (dbus.we_o != 0)
            rx_reg_read.next = dbus.en_o and (dbus.we_o == 0) and (dbus.adr_o[4:2] == 0)

        @always_comb
        def write_decode():
            # TX data writes are handed to the TX state machine as a one-cycle pulse.
            tx_reg_write.next = write_cycle and (dbus.adr_o[4:2] == 0) and not tx_buffer_valid
            tx_reg_write_data.next = dbus.db_wr[8:0]

        @always_comb
        def read_mux():
            read_data.next = 0

            if dbus.adr_o[4:2] == 0:
                read_data.next[8:0] = rx_data
                if ext_mode_en:
                    read_data.next[31] = rx_framing_error
            elif dbus.adr_o[4:2] == 1:
                read_data.next[0] = rx_ready
                read_data.next[1] = tx_ready
                read_data.next[2] = tx_busy
                if ext_mode_en:
                    read_data.next[3] = False
                    read_data.next[20:16] = self.fifo_bits
            elif dbus.adr_o[4:2] == 2:
                read_data.next[16:0] = tx_divider
                read_data.next[16] = enabled_q
                read_data.next[17] = ext_mode_en
                read_data.next[18 + self.fifo_bits:18] = fifo_threshold
            elif dbus.adr_o[4:2] == 3:
                read_data.next[0] = rx_int_en
                read_data.next[1] = tx_int_en
                read_data.next[3] = fifo_int_en
                if ext_mode_en:
                    read_data.next[16] = rx_pending
                    read_data.next[17] = tx_pending
                    read_data.next[19] = False

        @always_seq(clock.posedge, reset=reset)
        def register_write():
            if write_cycle:
                if dbus.adr_o[4:2] == 2:
                    tx_divider.next = dbus.db_wr[16:0]
                    enabled_q.next = dbus.db_wr[16]
                    ext_mode_en.next = dbus.db_wr[17]
                    fifo_threshold.next = dbus.db_wr[18 + self.fifo_bits:18]
                elif dbus.adr_o[4:2] == 3:
                    rx_int_en.next = dbus.db_wr[0]
                    tx_int_en.next = dbus.db_wr[1]
                    fifo_int_en.next = dbus.db_wr[3]

        return instances()

    @block
    def rx_state_machine(
        self,
        clock: BitSignal,
        reset: BitSignal,
        rx: BitSignal,
        tx_divider: Any,
        rx_data: Any,
        rx_ready: Any,
        rx_framing_error: Any,
        rx_reg_read: Any,
    ) -> Any:
        rx_busy = Signal(bool(0))
        rx_shift = Signal(modbv(0)[8:])
        rx_bit_index = Signal(modbv(0)[4:])
        rx_div_count = Signal(modbv(0)[16:])
        rx_sync_1 = Signal(bool(1))
        rx_sync_2 = Signal(bool(1))

        @always_seq(clock.posedge, reset=reset)
        def rx_fsm():
            rx_sync_1.next = rx
            rx_sync_2.next = rx_sync_1

            if rx_reg_read:
                rx_ready.next = False
                rx_framing_error.next = False

            if rx_busy:
                if rx_div_count == 0:
                    rx_div_count.next = tx_divider
                    if rx_bit_index < 8:
                        rx_shift.next[rx_bit_index] = rx_sync_2
                        rx_bit_index.next = rx_bit_index + 1
                    else:
                        rx_data.next = rx_shift
                        rx_ready.next = True
                        rx_framing_error.next = not rx_sync_2
                        rx_busy.next = False
                        rx_bit_index.next = 0
                else:
                    rx_div_count.next = rx_div_count - 1
            elif rx_sync_2 == 0:
                # Start bit detected.  Sample first data bit at 1.5 bit times.
                rx_busy.next = True
                rx_bit_index.next = 0
                rx_div_count.next = tx_divider + (tx_divider >> 1)

        return instances()

    @block
    def tx_state_machine(
        self,
        clock: BitSignal,
        reset: BitSignal,
        tx: BitSignal,
        tx_divider: Any,
        tx_busy: Any,
        tx_buffer_valid: Any,
        tx_reg_write: Any,
        tx_reg_write_data: Any,
    ) -> Any:
        tx_line = Signal(bool(1))
        tx_buffer = Signal(modbv(0)[8:])
        tx_shift = Signal(modbv(0)[8:])
        tx_bit_index = Signal(modbv(0)[4:])
        tx_div_count = Signal(modbv(0)[16:])

        @always_comb
        def tx_output():
            tx.next = tx_line

        @always_seq(clock.posedge, reset=reset)
        def tx_fsm():
            if tx_busy:
                if tx_div_count == 0:
                    tx_div_count.next = tx_divider
                    if tx_bit_index < 8:
                        # Data bits are sent LSB first, matching standard 8N1 UART.
                        tx_line.next = tx_shift[tx_bit_index]
                        tx_bit_index.next = tx_bit_index + 1
                    elif tx_bit_index == 8:
                        tx_line.next = True
                        tx_bit_index.next = 9
                    else:
                        if tx_buffer_valid:
                            tx_shift.next = tx_buffer
                            tx_buffer_valid.next = False
                            tx_line.next = False
                            tx_bit_index.next = 0
                        elif tx_reg_write:
                            tx_shift.next = tx_reg_write_data
                            tx_line.next = False
                            tx_bit_index.next = 0
                        else:
                            tx_busy.next = False
                            tx_line.next = True
                            tx_bit_index.next = 0
                else:
                    tx_div_count.next = tx_div_count - 1

                if tx_reg_write and not (tx_div_count == 0 and tx_bit_index == 9 and not tx_buffer_valid):
                    tx_buffer.next = tx_reg_write_data
                    tx_buffer_valid.next = True
            elif tx_reg_write:
                tx_busy.next = True
                tx_shift.next = tx_reg_write_data
                tx_line.next = False
                tx_bit_index.next = 0
                tx_div_count.next = tx_divider

        return instances()

    @block
    def createInstance(
        self,
        dbus: DbusBundle,
        clock: BitSignal,
        reset: BitSignal,
        tx: BitSignal,
        rx: BitSignal,
        irq: BitSignal,
        enabled: BitSignal,
    ) -> Any:
        assert dbus.xlen == 32, "BonfireUart currently supports a 32-bit DBus"

        tx_divider = Signal(modbv(0xFFFF)[16:])
        ext_mode_en = Signal(bool(0))
        enabled_q = Signal(bool(0))
        fifo_threshold = Signal(modbv(0)[self.fifo_bits:])

        tx_busy = Signal(bool(0))
        tx_buffer_valid = Signal(bool(0))
        tx_reg_write = Signal(bool(0))
        tx_reg_write_data = Signal(modbv(0)[8:])
        rx_data = Signal(modbv(0)[8:])
        rx_ready = Signal(bool(0))
        rx_framing_error = Signal(bool(0))
        rx_reg_read = Signal(bool(0))

        register_i = self.registers(
            dbus,
            clock,
            reset,
            irq,
            enabled,
            tx_divider,
            ext_mode_en,
            enabled_q,
            fifo_threshold,
            tx_busy,
            tx_buffer_valid,
            tx_reg_write,
            tx_reg_write_data,
            rx_data,
            rx_ready,
            rx_framing_error,
            rx_reg_read,
        )
        rx_i = self.rx_state_machine(
            clock,
            reset,
            rx,
            tx_divider,
            rx_data,
            rx_ready,
            rx_framing_error,
            rx_reg_read,
        )
        tx_i = self.tx_state_machine(
            clock,
            reset,
            tx,
            tx_divider,
            tx_busy,
            tx_buffer_valid,
            tx_reg_write,
            tx_reg_write_data,
        )

        return instances()

from __future__ import print_function

from myhdl import *

from rtl import bonfire_interfaces
from tb import ClkDriver
from tb.uncore.tb_wishbone_bfm import Wishbone_bfm
from tb.uncore.uart.uart_capture import UartCaptureResult, uart_tx_capture


class BonfireCoreSoCTestbench:
    def __init__(self, soc, conversion=False):
        self.soc = soc
        self.conversion = conversion

    @block
    def testbench(self):
        sysclk = Signal(bool(0))
        resetn = Signal(bool(1))
        num_leds = self.soc.numLeds
        led = Signal(modbv(0)[num_leds:])
        led_sim = Signal(modbv(0)[num_leds:])
        uart0_txd = Signal(bool(1))
        uart0_rxd = Signal(bool(1))
        jtag_tck = Signal(bool(0))
        jtag_tms = Signal(bool(1))
        jtag_tdi = Signal(bool(0))
        jtag_tdo = Signal(bool(0))
        jtag_trstn = Signal(bool(1))

        o_resetn = Signal(bool(1))
        i_locked = Signal(bool(0))
        old_led = Signal(modbv(0)[num_leds:])
        uart_capture_stop = Signal(bool(0))

        clk_driver_i = ClkDriver.ClkDriver(sysclk, period=10)

        self.soc.conversion = self.conversion

        if self.soc.exposeWishboneMaster:
            wb_master = bonfire_interfaces.Wishbone_master_bundle()
        else:
            wb_master = None

        if self.soc.enableJtagDebug:
            soc_i = self.soc.bonfire_core_soc(
                sysclk, resetn, uart0_txd, uart0_rxd, led, o_resetn, i_locked,
                wb_master=wb_master,
                jtag_tck=jtag_tck,
                jtag_tms=jtag_tms,
                jtag_tdi=jtag_tdi,
                jtag_tdo=jtag_tdo,
                jtag_trstn=jtag_trstn,
            )
        else:
            soc_i = self.soc.bonfire_core_soc(sysclk, resetn, uart0_txd, uart0_rxd, led, o_resetn, i_locked, wb_master=wb_master)

        if self.soc.exposeWishboneMaster:
            wb_bfm = Wishbone_bfm()
            wb_i = wb_bfm.Wishbone_check(wb_master, sysclk, self.soc.reset_signal)

        if self.soc.uartLoopback:
            @always_comb
            def uart_loopback():
                uart0_rxd.next = uart0_txd

        if self.soc.uartCapture and not self.conversion:
            uart_capture_result = UartCaptureResult()
            uart_capture_i = uart_tx_capture(
                uart0_txd,
                bit_time=self.soc.uartCaptureBitTime,
                result=uart_capture_result,
                stop=uart_capture_stop,
                echo_output=True,
                expected_signature=self.soc.uartCaptureExpected,
            )

            @instance
            def uart_capture_report():
                while not uart_capture_stop:
                    yield sysclk.posedge
                if self.soc.uartCaptureRequireLedSuccess:
                    while led_sim != led_sim.max - 1:
                        yield sysclk.posedge
                print("")
                print("UART capture bytes: %d" % uart_capture_result.total_count)
                print("UART capture framing errors: %d" % uart_capture_result.framing_errors)
                print("UART capture signature ok: %s" % uart_capture_result.signature_ok)
                if self.soc.uartCaptureRequireLedSuccess:
                    print("UART loopback LED success: %s" % led_sim)
                raise StopSimulation

        if self.soc.ledActiveLow:
            @always_comb
            def led_active_low_decode():
                led_sim.next = ~led
        else:
            @always_comb
            def led_active_high_decode():
                led_sim.next = led

        @always(sysclk.posedge)
        def observer():
            if led_sim != old_led:
                print("LED status @%s ns: %s" % (now(), led_sim))
                old_led.next = led_sim
                if led_sim.val == led_sim.max - 1 and not (
                        self.soc.uartCapture and not self.conversion):
                    raise StopSimulation

        @instance
        def do_reset():
            for i in range(5):
                yield sysclk.posedge
            i_locked.next = True

        return instances()

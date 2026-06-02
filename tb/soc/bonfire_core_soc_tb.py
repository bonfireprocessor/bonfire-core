from __future__ import print_function

from myhdl import *

from rtl import bonfire_interfaces
from tb import ClkDriver
from tb.uncore.tb_wishbone_bfm import Wishbone_bfm


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
        uart0_rxd = Signal(bool(0))

        o_resetn = Signal(bool(1))
        i_locked = Signal(bool(0))
        old_led = Signal(modbv(0)[num_leds:])

        clk_driver_i = ClkDriver.ClkDriver(sysclk, period=10)

        self.soc.conversion = self.conversion

        if self.soc.exposeWishboneMaster:
            wb_master = bonfire_interfaces.Wishbone_master_bundle()
        else:
            wb_master = None

        soc_i = self.soc.bonfire_core_soc(sysclk, resetn, uart0_txd, uart0_rxd, led, o_resetn, i_locked, wb_master=wb_master)

        if self.soc.exposeWishboneMaster:
            wb_bfm = Wishbone_bfm()
            wb_i = wb_bfm.Wishbone_check(wb_master, sysclk, self.soc.reset_signal)

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
                if led_sim.val == led_sim.max - 1:
                    raise StopSimulation

        @instance
        def do_reset():
            for i in range(5):
                yield sysclk.posedge
            i_locked.next = True

        return instances()

from __future__ import print_function

from myhdl import *

from rtl import bonfire_interfaces, config
from rtl.soc.bonfire_core_soc import BonfireCoreSoC
from tb import ClkDriver
from tb.uncore.tb_wishbone_bfm import Wishbone_bfm


class BonfireCoreSoCTestbench:
    def __init__(self, config=config.BonfireConfig(), hexfile="", soc_config={}, expose_wishbone=False, conversion=False):
        self.config = config
        self.hexfile = hexfile
        self.soc_config = dict(soc_config)
        self.expose_wishbone = expose_wishbone
        self.conversion = conversion
        if expose_wishbone:
            self.soc_config["exposeWishboneMaster"] = True

    @block
    def testbench(self):
        sysclk = Signal(bool(0))
        resetn = Signal(bool(1))
        num_leds = self.soc_config.get("numLeds", 4)
        led = Signal(modbv(0)[num_leds:])
        uart0_txd = Signal(bool(1))
        uart0_rxd = Signal(bool(0))

        o_resetn = Signal(bool(1))
        i_locked = Signal(bool(0))
        old_led = Signal(modbv(0)[num_leds:])

        clk_driver_i = ClkDriver.ClkDriver(sysclk, period=10)

        local_soc_config = dict(self.soc_config)
        local_soc_config["ledActiveLow"] = False
        soc = BonfireCoreSoC(self.config, hexfile=self.hexfile, soc_config=local_soc_config)
        soc.conversion = self.conversion

        if self.expose_wishbone:
            wb_master = bonfire_interfaces.Wishbone_master_bundle()
        else:
            wb_master = None

        soc_i = soc.bonfire_core_soc(sysclk, resetn, uart0_txd, uart0_rxd, led, o_resetn, i_locked, wb_master=wb_master)

        if self.expose_wishbone:
            wb_bfm = Wishbone_bfm()
            wb_i = wb_bfm.Wishbone_check(wb_master, sysclk, soc.reset_signal)

        @always(sysclk.posedge)
        def observer():
            if led != old_led:
                print("LED status @%s ns: %s" % (now(), led))
                old_led.next = led
                if led.val == led.max - 1:
                    raise StopSimulation

        @instance
        def do_reset():
            for i in range(5):
                yield sysclk.posedge
            i_locked.next = True

        return instances()

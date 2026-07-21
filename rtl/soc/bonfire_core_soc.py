from __future__ import annotations, print_function

from typing import Any, Mapping

from myhdl import *

from rtl.bonfire_interfaces import DbusBundle, Wishbone_master_bundle
from rtl.config import BonfireConfig
from rtl.debug import DmiBundle, Ecp5JtaggClient, Ecp5JtaggInputBundle, Ecp5JtaggOutputBundle
from rtl.debug.jtag_dtm import JtagDTM
from rtl.type_aliases import BitSignal
from rtl.uncore import bonfire_core_ex, ram_dp
from rtl.uncore.dbus_interconnect import AdrMask, DbusInterConnects
from rtl.uncore.uart import BonfireUart
from rtl import bonfire_interfaces,config
from util.diagnostics import get_diagnostics


class BonfireCoreSoC:
    WISHBONE_DUMMY_SIGNATURE = 0x44554D59  # ASCII "DUMY"

    def __init__(self, config: BonfireConfig, hexfile: str = "", soc_config: Mapping[str, Any] | None = None) -> None:
        soc_config = soc_config or {}

        self.config: BonfireConfig = config
        self.hexfile: str = hexfile
        self.bramMask: AdrMask = AdrMask(32,28,0xc)
        self.dbusMask: AdrMask = AdrMask(32,28,0x8)
        self.ledMask: AdrMask = AdrMask(32,16,0x8000)
        self.uartMask: AdrMask = AdrMask(32,16,0x8001)
        self.wbMask: AdrMask = AdrMask(32,28,0x4)
        self.resetAdr: int = soc_config.get('resetAdr', 0xc0000000)
        self.bramAdrWidth: int = soc_config.get('bramAdrWidth', 11)
        self.NoReset: bool = soc_config.get('NoReset', False)
        self.lanedMemory: bool = soc_config.get('lanedMemory', True)
        self.numLeds: int = soc_config.get('numLeds', 4)
        self.ledActiveLow: bool = soc_config.get('ledActiveLow', True)
        self.UseVHDLMemory: bool = soc_config.get('UseVHDLMemory', False) # not used yet
        self.exposeWishboneMaster: bool = soc_config.get('exposeWishboneMaster', False)
        self.registerWishboneDbus: bool = soc_config.get('registerWishboneDbus', False)
        self.enableJtagDebug: bool = soc_config.get('enableJtagDebug', False)
        self.debugJtagTransport: str = soc_config.get('debugJtagTransport', 'native')
        assert self.debugJtagTransport in ('native', 'ecp5_jtagg'), (
            "debugJtagTransport must be 'native' or 'ecp5_jtagg'"
        )
        self.uartLoopback: bool = soc_config.get('uartLoopback', False)
        self.uartCapture: bool = soc_config.get('uartCapture', False)
        self.uartCaptureBitTime: int = soc_config.get('uartCaptureBitTime', 2170)
        self.uartCaptureExpected: tuple[int, ...] | None = soc_config.get('uartCaptureExpected', None)
        self.uartCaptureRequireLedSuccess: bool = soc_config.get('uartCaptureRequireLedSuccess', False)
        self.config.enableDebugNdmreset = bool(soc_config.get('enableDebugNdmreset', self.config.enableDebugNdmreset))
        self.conversion: bool = False
        self.reset_signal: BitSignal | None = None



    @block
    def led_out(self, clock: BitSignal, reset: BitSignal, led: Any, dbus: DbusBundle,
                ledactiveLow: bool = False) -> Any:
        num_leds = len(led)

        led_reg = Signal(modbv(0)[num_leds:]);

        assert num_leds>0 and num_leds<=8, "Invalid Value for number of Leds"

        if ledactiveLow:
            @always_comb
            def led_inv():
                led.next = ~led_reg
        else:
            @always_comb
            def led_buf():
                led.next = led_reg

        @always_seq(clock.posedge,reset=reset)
        def seq():
            if dbus.en_o:
                if  dbus.we_o[0]:
                    led_reg.next[num_leds:0] = dbus.db_wr[num_leds:0]
               
                    
        @always_comb
        def comb():
            dbus.ack_i.next = dbus.en_o
            dbus.error_i.next = False
            dbus.stall_i.next = False
            dbus.db_rd.next = 0
            if dbus.en_o:
                dbus.db_rd.next[num_leds:0] = led_reg


        return instances()

    @block
    def wishbone_dummy(self, clock: BitSignal, reset: BitSignal, wb_bundle: Wishbone_master_bundle) -> Any:
        @always_comb
        def comb():
            if wb_bundle.wbm_cyc_o and wb_bundle.wbm_stb_o:
                wb_bundle.wbm_ack_i.next = True
                wb_bundle.wbm_db_i.next = self.WISHBONE_DUMMY_SIGNATURE
            else:
                wb_bundle.wbm_ack_i.next = False
                wb_bundle.wbm_db_i.next = 0


        if not self.conversion:
            @always_seq(clock.posedge,reset=reset)
            def monitor():
                if wb_bundle.wbm_cyc_o and wb_bundle.wbm_stb_o and wb_bundle.wbm_ack_i:
                    diagnostics = get_diagnostics()
                    diagnostics.detail("wishbone dummy:")
                    diagnostics.detail("  adr_o: 0x{:08x}".format(int(wb_bundle.wbm_adr_o<<2)))
                    if wb_bundle.wbm_we_o:
                        diagnostics.detail("  write: 0x{:08x}".format(int(wb_bundle.wbm_db_o)))
                    else:
                        diagnostics.detail("  read: 0x{:08x}".format(int(wb_bundle.wbm_db_i)))
                    diagnostics.detail("  dat_o: 0x{:08x}".format(int(wb_bundle.wbm_db_o)))
                    diagnostics.detail("  cyc_o: 0x{:x}".format(int(wb_bundle.wbm_cyc_o)))
                    diagnostics.detail("  stb_o: 0b{:b}".format(int(wb_bundle.wbm_stb_o)))
                    diagnostics.detail("  we_o: 0b{:b}".format(int(wb_bundle.wbm_we_o)))
                    diagnostics.detail("  sel_o: 0b{:b}".format(int(wb_bundle.wbm_sel_o)))


        return instances()

    @block
    def reset_logic(self, clock: BitSignal, resetn: BitSignal, o_resetn: BitSignal,
                    i_locked: BitSignal, reset: BitSignal) -> Any:
        """"
        clock : clock signal
        resetn : in, bool, reset button, active low
        o_resetn : in, bool, Reset PLL, active low
        i_locked: in, bool, PLL locked
        reset : out, bool,  Reset to logic
        """

        res1: BitSignal = Signal(bool(0))
        res2: BitSignal = Signal(bool(0))

        dummy: BitSignal = Signal(bool(1))

        @always_comb
        def set_out():
            o_resetn.next = dummy


        @always(clock.posedge)
        def res():
            res1.next = not resetn or not i_locked
            res2.next = res1
            reset.next = res2

        return instances()

    @block
    def no_reset_logic(self, clock: BitSignal, resetn: BitSignal, o_resetn: BitSignal,
                       i_locked: BitSignal, reset: BitSignal) -> Any:
        """"
        clock : clock signal
        resetn : in, bool, reset button, active low
        o_resetn : in, bool, Reset PLL, active low
        i_locked: in, bool, PLL locked
        reset : out, bool,  Reset to logic
        """

        dummy: BitSignal = Signal(bool(0))

        @always_comb
        def dummy_logic():
            o_resetn.next = not dummy
            reset.next = dummy


        return instances()


    @block
    def bonfire_core_soc(self, sysclk: BitSignal, resetn: BitSignal, uart0_tx: BitSignal,
                         uart0_rx: BitSignal, led: Any, o_resetn: BitSignal,
                         i_locked: BitSignal,
                         wb_master: Wishbone_master_bundle | None = None,
                         jtag_tck: BitSignal | None = None,
                         jtag_tms: BitSignal | None = None,
                         jtag_tdi: BitSignal | None = None,
                         jtag_tdo: BitSignal | None = None,
                         jtag_trstn: BitSignal | None = None,
                         jtagg_i: Ecp5JtaggInputBundle | None = None,
                         jtagg_o: Ecp5JtaggOutputBundle | None = None) -> Any:
        """
        sysclk : cpu clock
        resetn : reset button, active low
        uart0_tx : UART TX Signal
        uart0_rx: UART RX Signal
        led : modbv vector for led(s)
        o_resetn : Output, reset PLL
        wb_master : Optional Wishbone Master Interface
        """

        self.config.reset_address=self.resetAdr

        sys_reset: BitSignal = ResetSignal(0,active=1,isasync=False)
        core_reset: BitSignal = ResetSignal(0,active=1,isasync=False)
        self.reset_signal = core_reset

        native_dbus: DbusBundle = bonfire_interfaces.DbusBundle(config)
        led_dbus: DbusBundle = bonfire_interfaces.DbusBundle(config)
        uart_dbus: DbusBundle = bonfire_interfaces.DbusBundle(config)
        if wb_master is None:
            wb_master_local: Wishbone_master_bundle = bonfire_interfaces.Wishbone_master_bundle()
        else:
            wb_master_local = wb_master
        bram_port_a = ram_dp.RamPort32(adrWidth=self.bramAdrWidth, readOnly=True)
        bram_port_b = ram_dp.RamPort32(adrWidth=self.bramAdrWidth)



        if self.lanedMemory:
            get_diagnostics().detail("soc: using laned memory")
            ram = ram_dp.DualportedRamLaned(self.hexfile,adrwidth=self.bramAdrWidth)
        else:
            get_diagnostics().detail("soc: using non-laned memory")
            ram = ram_dp.DualportedRam(self.hexfile,adrwidth=self.bramAdrWidth)

        ram_i = ram.ram_instance(bram_port_a,bram_port_b,sysclk)

        native_io_i = DbusInterConnects.Master8Slaves(
            native_dbus,
            sysclk,
            core_reset,
            slave0=led_dbus,
            slave1=uart_dbus,
            adrmask0=self.ledMask,
            adrmask1=self.uartMask,
        )

        led_out_i=self.led_out(sysclk,core_reset,led,led_dbus, ledactiveLow=self.ledActiveLow)

        if not self.exposeWishboneMaster:
            wb_i = self.wishbone_dummy(sysclk,core_reset,wb_master_local)

        uart_irq = Signal(bool(0))
        uart_enabled = Signal(bool(0))
        uart_i = BonfireUart().createInstance(
            uart_dbus, sysclk, core_reset, uart0_tx, uart0_rx,
            uart_irq, uart_enabled)

        if self.NoReset:
            reset_i = self.no_reset_logic(sysclk,resetn,o_resetn,i_locked,sys_reset)
        else:
            reset_i = self.reset_logic(sysclk,resetn,o_resetn,i_locked,sys_reset)

        debug_transport: DmiBundle | None = None
        if self.enableJtagDebug:
            debug_transport = DmiBundle(self.config)
            if self.debugJtagTransport == 'native':
                assert jtag_tck is not None, "native JTAG debug requires jtag_tck"
                assert jtag_tms is not None, "native JTAG debug requires jtag_tms"
                assert jtag_tdi is not None, "native JTAG debug requires jtag_tdi"
                assert jtag_tdo is not None, "native JTAG debug requires jtag_tdo"
                assert jtag_trstn is not None, "native JTAG debug requires jtag_trstn"
                jtag_i = JtagDTM(self.config).createInstance(
                    sysclk, sys_reset, jtag_tck, jtag_tms, jtag_tdi, jtag_trstn,
                    jtag_tdo, debug_transport)
            else:
                assert jtagg_i is not None, "ECP5 JTAGG debug requires jtagg_i"
                assert jtagg_o is not None, "ECP5 JTAGG debug requires jtagg_o"
                jtagg_client_i = Ecp5JtaggClient(
                    self.config, sysclk, sys_reset, jtagg_i, jtagg_o,
                    debug_transport)

        if self.config.enableDebugNdmreset and debug_transport is not None:
            @always_comb
            def core_reset_comb():
                core_reset.next = sys_reset or debug_transport.ndmreset
        else:
            @always_comb
            def core_reset_comb():
                core_reset.next = sys_reset

        core_i = bonfire_core_ex.bonfireCoreExtendedInterface(wb_master_local,native_dbus,bram_port_a,bram_port_b,
                                                              sysclk,core_reset,config=self.config,
                                                              wb_mask=self.wbMask,
                                                              db_mask=self.dbusMask,
                                                              bram_mask=self.bramMask,
                                                              register_wishbone_dbus=self.registerWishboneDbus,
                                                              debugTransportBundle=debug_transport)


        return instances()

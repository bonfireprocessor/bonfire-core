from __future__ import print_function

from myhdl import *

from  uncore import bonfire_core_ex,ram_dp
from uncore.dbus_interconnect import AdrMask
from rtl import bonfire_interfaces,config


class BonfireCoreSoC:
    def __init__(self,config,hexfile=""):
        self.config = config
        self.hexfile = hexfile
        self.bramMask = AdrMask(32,28,0xc)
        self.dbusMask = AdrMask(32,28,0x8)
        self.wbMask = AdrMask(32,28,0x4)
        self.resetAdr=0xc0000000
        self.bramAdrWidth=11
        self.NoReset=False
        self.LanedMemory=True
        self.numLeds=4
        self.ledActiveLow = True
        self.UseVHDLMemory = False



    @block
    def led_out(self,clock,reset,led,dbus):
        num_leds = len(led)

        assert num_leds>0 and num_leds<=8, "Invalid Value for number of Leds"

        @always_seq(clock.posedge,reset=reset)
        def seq():
            if dbus.en_o and dbus.we_o[0]:
                led.next[num_leds:0] = dbus.db_wr[num_leds:0]

        @always_comb
        def comb():
            dbus.ack_i.next = dbus.en_o
            dbus.stall_i.next = False

        return instances()

    @block
    def wishbone_dummy(self,wb_bundle):

        @always_comb
        def wb_ack():
            wb_bundle.wbm_ack_i.next = wb_bundle.wbm_cyc_o and wb_bundle.wbm_stb_o
            wb_bundle.wbm_db_i.next = 0xdeadbeef

        return instances()

    @block
    def uart_dummy(self,uart_tx,uart_rx):

        @always_comb
        def loopback():
            uart_tx.next = uart_rx


        return instances()

    @block
    def reset_logic(self,clock,resetn,o_resetn,i_locked, reset):
        """"
        clock : clock signal
        resetn : in, bool, reset button, active low
        o_resetn : in, bool, Reset PLL, active low
        i_locked: in, bool, PLL locked
        reset : out, bool,  Reset to logic
        """

        res1 = Signal(bool(0))
        res2= Signal(bool(0))

        dummy=Signal(bool(1))

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
    def no_reset_logic(self,clock,resetn,o_resetn,i_locked, reset):
        """"
        clock : clock signal
        resetn : in, bool, reset button, active low
        o_resetn : in, bool, Reset PLL, active low
        i_locked: in, bool, PLL locked
        reset : out, bool,  Reset to logic
        """

        dummy=Signal(bool(0))

        @always_comb
        def dummy_logic():
            o_resetn.next = not dummy
            reset.next = dummy


        return instances()


    @block
    def bonfire_core_soc(self,sysclk,resetn,uart0_tx,uart0_rx,led,o_resetn,i_locked):
        """
        sysclk : cpu clock
        resetn : reset button, active low
        uart0_tx : UART TX Signal
        uart0_rx: UART RX Signal
        led : modbv vector for led(s)
        o_resetn : Output, reset PLL
        """

        self.config.reset_address=self.resetAdr

        reset=ResetSignal(0,active=1,isasync=False)

        dbus = bonfire_interfaces.DbusBundle(config)
        wb_master = bonfire_interfaces.Wishbone_master_bundle()
        bram_port_a = ram_dp.RamPort32(readOnly=True)
        bram_port_b = ram_dp.RamPort32()

        if self.LanedMemory:
            ram = ram_dp.DualportedRamLaned(self.hexfile,adrwidth=self.bramAdrWidth)
        else:
            ram = ram_dp.DualportedRam(self.hexfile,adrwidth=self.bramAdrWidth)

        ram_i = ram.ram_instance(bram_port_a,bram_port_b,sysclk)

        if self.ledActiveLow:
            n_led = Signal(modbv(0)[len(led):])
            led_out_i=self.led_out(sysclk,reset,n_led,dbus)

            @always_comb
            def led_inv_proc():
                led.next = ~n_led

        else:
            led_out_i = self.led_out(sysclk,reset,led,dbus)

        wb_i = self.wishbone_dummy(wb_master)

        uart_i = self.uart_dummy(uart0_tx,uart0_rx)

        if self.NoReset:
            reset_i = self.no_reset_logic(sysclk,resetn,o_resetn,i_locked,reset)
        else:
            reset_i = self.reset_logic(sysclk,resetn,o_resetn,i_locked,reset)

        core_i = bonfire_core_ex.bonfireCoreExtendedInterface(wb_master,dbus,bram_port_a,bram_port_b,
                                                              sysclk,reset,config=self.config,
                                                              wb_mask=self.wbMask,
                                                              db_mask=self.dbusMask,
                                                              bram_mask=self.bramMask)


        return instances()

    @block
    def soc_testbench(self):

        from tb import ClkDriver

        sysclk = Signal(bool(0))
        resetn = Signal(bool(1))
        LED = Signal(modbv(0)[self.numLeds:])
        uart0_txd = Signal(bool(1))
        uart0_rxd = Signal(bool(0))

        o_resetn = Signal(bool(1))
        i_locked = Signal(bool(0))

        old_led = Signal(modbv(0)[self.numLeds:])

        clk_driver_i=ClkDriver.ClkDriver(sysclk,period=10)

        self.ledActiveLow = False

        inst = self.bonfire_core_soc(sysclk,resetn,uart0_txd,uart0_rxd,LED,o_resetn,i_locked)

        @always(sysclk.posedge)
        def observer():
            if LED != old_led:
                print("LED status %s: %s" % (now(),LED))
                old_led.next = LED
                if LED.val==LED.max-1:
                    raise StopSimulation


        @instance
        def do_reset():

            for i in range(5):
                yield sysclk.posedge
            i_locked.next = True



        return instances()



    def gen_soc(self,hdl,name,path,gentb=False):
        from myhdl import ToVHDLWarning
        import warnings

        if gentb:
            inst = self.soc_testbench()
        else:    

            sysclk = Signal(bool(0))
            resetn = Signal(bool(1))
            LED = Signal(modbv(0)[self.numLeds:])
            uart0_txd = Signal(bool(1))
            uart0_rxd = Signal(bool(0))

            o_resetn = Signal(bool(1))
            i_locked = Signal(bool(0))


            inst = self.bonfire_core_soc(sysclk,resetn,uart0_txd,uart0_rxd,LED,o_resetn,i_locked)

        with warnings.catch_warnings():
            warnings.filterwarnings(
                'default',
                category=ToVHDLWarning)
            inst.convert(hdl=hdl, std_logic_ports=True, initial_values=True, path=path, name=name)









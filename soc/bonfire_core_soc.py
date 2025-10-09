from __future__ import print_function

from myhdl import *

from  uncore import bonfire_core_ex,ram_dp
from uncore.dbus_interconnect import AdrMask
from rtl import bonfire_interfaces,config


class BonfireCoreSoC:
    def __init__(self,config,hexfile="",soc_config={}):
        self.config = config
        self.hexfile = hexfile
        self.bramMask = AdrMask(32,28,0xc)
        self.dbusMask = AdrMask(32,28,0x8)
        self.wbMask = AdrMask(32,28,0x4)
        self.resetAdr = soc_config.get('resetAdr', 0xc0000000)
        self.bramAdrWidth = soc_config.get('bramAdrWidth', 11)
        self.NoReset = soc_config.get('NoReset', False)
        self.LanedMemory = soc_config.get('LanedMemory', True)
        self.numLeds = soc_config.get('numLeds', 4)
        self.ledActiveLow = soc_config.get('ledActiveLow', True)
        self.UseVHDLMemory = soc_config.get('UseVHDLMemory', False) # not used yet
        self.exposeWishboneMaster = soc_config.get('exposeWishboneMaster', False)
        self.conversion=False



    @block
    def led_out(self,clock,reset,led,dbus, ledactiveLow=False):
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
            dbus.stall_i.next = False
            dbus.db_rd.next = 0
            if dbus.en_o:
                dbus.db_rd.next[num_leds:0] = led_reg


        return instances()

    @block
    def wishbone_dummy(self,clock,reset,wb_bundle):

        dummy_reg = Signal(modbv(0xdeadbeef)[32:])

        @always_seq(clock.posedge,reset=reset)
        def regwrite():
            if wb_bundle.wbm_cyc_o and wb_bundle.wbm_stb_o and wb_bundle.wbm_we_o:
                dummy_reg.next = wb_bundle.wbm_db_o

        @always_comb
        def comb():
            if wb_bundle.wbm_cyc_o and wb_bundle.wbm_stb_o:
                wb_bundle.wbm_ack_i.next = True
                wb_bundle.wbm_db_i.next = dummy_reg
            else:
                wb_bundle.wbm_ack_i.next = False
                wb_bundle.wbm_db_i.next = 0


        if not self.conversion:
            @always_seq(clock.posedge,reset=reset)
            def monitor():
                if wb_bundle.wbm_cyc_o and wb_bundle.wbm_stb_o and wb_bundle.wbm_ack_i:
                    print("Wishbone Dummy:")
                    print("adr_o: 0x{:08x}".format(int(wb_bundle.wbm_adr_o<<2)))
                    if wb_bundle.wbm_we_o:
                        print("Write: 0x{:08x}".format(int(wb_bundle.wbm_db_o)))
                    else:
                        print("Read : 0x{:08x}".format(int(wb_bundle.wbm_db_i)))
                    print("dat_o: 0x{:08x}".format(int(wb_bundle.wbm_db_o)))
                    print("cyc_o: 0x{:x}".format(int(wb_bundle.wbm_cyc_o)))
                    print("stb_o: 0b{:b}".format(int(wb_bundle.wbm_stb_o)))
                    print("we_o: 0b{:b}".format(int(wb_bundle.wbm_we_o)))
                    print("sel_o: 0b{:b}".format(int(wb_bundle.wbm_sel_o)))


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
    def bonfire_core_soc(self,sysclk,resetn,uart0_tx,uart0_rx,led,o_resetn,i_locked,wb_master=None):
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

        reset=ResetSignal(0,active=1,isasync=False)

        dbus = bonfire_interfaces.DbusBundle(config)
        if wb_master is None:
            wb_master_local = bonfire_interfaces.Wishbone_master_bundle()
        else:
            wb_master_local = wb_master
        bram_port_a = ram_dp.RamPort32(readOnly=True)
        bram_port_b = ram_dp.RamPort32()



        if self.LanedMemory:
            print("Using Laned Memory")
            ram = ram_dp.DualportedRamLaned(self.hexfile,adrwidth=self.bramAdrWidth)
        else:
            print("Using non-laned Memory")
            ram = ram_dp.DualportedRam(self.hexfile,adrwidth=self.bramAdrWidth)

        ram_i = ram.ram_instance(bram_port_a,bram_port_b,sysclk)

        led_out_i=self.led_out(sysclk,reset,led,dbus, ledactiveLow=self.ledActiveLow)

        if not self.exposeWishboneMaster:
            wb_i = self.wishbone_dummy(sysclk,reset,wb_master_local)

        uart_i = self.uart_dummy(uart0_tx,uart0_rx)

        if self.NoReset:
            reset_i = self.no_reset_logic(sysclk,resetn,o_resetn,i_locked,reset)
        else:
            reset_i = self.reset_logic(sysclk,resetn,o_resetn,i_locked,reset)

        core_i = bonfire_core_ex.bonfireCoreExtendedInterface(wb_master_local,dbus,bram_port_a,bram_port_b,
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
                print("LED status @%s ns: %s" % (now(),LED))
                old_led.next = LED
                if LED.val==LED.max-1:
                    raise StopSimulation


        @instance
        def do_reset():

            for i in range(5):
                yield sysclk.posedge
            i_locked.next = True



        return instances()



    def gen_soc(self,hdl,name,path,gentb=False,handleWarnings='default'):
        from myhdl import ToVHDLWarning
        import warnings

        self.conversion=True

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

            if self.exposeWishboneMaster:
                print("Exposing Wishbone Master Interface")
                wb_master = bonfire_interfaces.Wishbone_master_bundle()
            else:
                wb_master = None

            inst = self.bonfire_core_soc(sysclk,resetn,uart0_txd,uart0_rxd,LED,o_resetn,i_locked,wb_master=wb_master)

        with warnings.catch_warnings():
            warnings.filterwarnings(
                handleWarnings,
                category=ToVHDLWarning)
            inst.convert(hdl=hdl, std_logic_ports=True, initial_values=True, path=path, name=name)




from __future__ import print_function

from myhdl import *

from  uncore import bonfire_core_ex,ram_dp,dbus_interconnect
from rtl import bonfire_interfaces,config


class BonfireCoreSoC:
    def __init__(self,config,hexfile=""):
        self.config = config
        self.hexfile = hexfile



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
    def bonfire_core_soc(self,sysclk,resetn,uart0_tx,uart0_rx,led,o_resetn,i_locked, LanedMemory=True):
        """
        sysclk : cpu clock
        resetn : reset button, active low
        uart0_tx : UART TX Signal
        uart0_rx: UART RX Signal
        led : modbv vector for led(s)
        o_resetn : Output, reset PLL
        """

        reset=ResetSignal(0,active=1,isasync=False)

        dbus = bonfire_interfaces.DbusBundle(config)
        wb_master = bonfire_interfaces.Wishbone_master_bundle()
        bram_port_a = ram_dp.RamPort32(readOnly=True)
        bram_port_b = ram_dp.RamPort32()

        if LanedMemory:
            ram = ram_dp.DualportedRamLaned(self.hexfile,adrwidth=11)
        else:
            ram = ram_dp.DualportedRam(self.hexfile,adrwidth=11)

        ram_i = ram.ram_instance(bram_port_a,bram_port_b,sysclk)


        led_out_i = self.led_out(sysclk,reset,led,dbus)

        uart_i = self.uart_dummy(uart0_tx,uart0_rx)

        reset_i = self.reset_logic(sysclk,resetn,o_resetn,i_locked,reset)

        core_i = bonfire_core_ex.bonfireCoreExtendedInterface(wb_master,dbus,bram_port_a,bram_port_b,sysclk,reset,config=self.config)


        return instances()


    def gen_soc(self,hdl,name,path,num_leds=4,LanedMemory=True):
        from myhdl import ToVHDLWarning
        import warnings

        sysclk = Signal(bool(0))
        resetn = Signal(bool(1))
        LED = Signal(modbv(0)[num_leds:])
        uart0_txd = Signal(bool(1))
        uart0_rxd = Signal(bool(0))

        o_resetn = Signal(bool(1))
        i_locked = Signal(bool(0))


        inst = self.bonfire_core_soc(sysclk,resetn,uart0_txd,uart0_rxd,LED,o_resetn,i_locked, LanedMemory=LanedMemory)

        with warnings.catch_warnings():
            warnings.filterwarnings(
                'default',
                category=ToVHDLWarning)
            inst.convert(hdl=hdl, std_logic_ports=True, initial_values=True, path=path, name=name)



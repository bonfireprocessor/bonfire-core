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
    def bonfire_core_soc(self,clock,reset,uart_tx,uart_rx,led):
        """      
        clock : cpu clock
        reset : reset signal
        uart_tx : UART TX Signal
        uart_rx: UART RX Signal
        led : modbv vector for led(s)
        """

        
        dbus = bonfire_interfaces.DbusBundle(config)
        wb_master = bonfire_interfaces.Wishbone_master_bundle()
        bram_port_a = ram_dp.RamPort32(readOnly=True)
        bram_port_b = ram_dp.RamPort32()

        ram = ram_dp.DualportedRam(self.hexfile)
        ram_i = ram.ram_instance(bram_port_a,bram_port_b,clock)
        
        led_out_i = self.led_out(clock,reset,led,dbus)

        core_i = bonfire_core_ex.bonfireCoreExtendedInterface(wb_master,dbus,bram_port_a,bram_port_b,clock,reset,config=self.config)
   
      
        return instances()
    
    
    def gen_soc(self,hdl,name,path,num_leds=4):
        from myhdl import ToVHDLWarning
        import warnings
        
        clock = Signal(bool(0))
        reset = ResetSignal(0, active=1, isasync=False)
        leds = Signal(modbv(0)[num_leds:])
        uart_tx = Signal(bool(1))
        uart_rx = Signal(bool(0))
                         
        
        inst = self.bonfire_core_soc(clock,reset,uart_tx,uart_rx,leds)
        
        with warnings.catch_warnings():
            warnings.filterwarnings(
                'default',
                category=ToVHDLWarning)
            inst.convert(hdl=hdl, std_logic_ports=True, initial_values=True, path=path, name=name)
        
        
        
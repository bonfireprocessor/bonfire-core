from __future__ import print_function

from myhdl import *

from rtl.loadstore import *


class sim_ram:
    def __init__(self):
        self.latency = 1

    def setLatency(self,latency):
        self.latency=latency


    @block
    def ram_interface(self,ram,bus,clock,reset,readOnly=False):
        """
            Instantiate a RAM interface  for simulation

            ram : RAM Array, should be [Signal(modbv(0)[32:]) for ii in range(0, ram_size)]
            bus: Data bus (class DbusBundle)
            clock, reset : Clock and reset 
        """        
       
        we_o = Signal(modbv(0)[bus.xlen/8:])
        db_wr = Signal(modbv(0)[bus.xlen:])       

        if not readOnly:
           
            @always_comb
            def wire_write():
                we_o.next = bus.we_o
                db_wr.next = bus.db_wr


        wait_states = Signal(intbv(0))  # Signal for simulating wait state logic 
        adr_reg = Signal(modbv(0)[32:0])
        write_reg = Signal(modbv(0)[32:0])
        we_reg = Signal(modbv(0)[4:])

        @always_comb
        def bus_stall():
            if self.latency>1:
                bus.stall_i.next = bus.en_o and wait_states>0
            else:
                bus.stall_i.next = False     


        @always(clock.posedge)
        def bus_slave():

            bus.ack_i.next=False

            must_wait = self.latency > 1

            if bus.en_o and must_wait and wait_states==0:
                wait_states.next = self.latency -1
                adr_reg.next = bus.adr_o
                write_reg.next = db_wr
                we_reg.next = we_o
                
            elif ( not must_wait and bus.en_o ) or wait_states != 0:

                if must_wait: 
                    w = wait_states - 1
                    wait_states.next = w
                else:
                    w = 0    

                if w==0: # When all wait states consumed ack bus cycle
                    if must_wait:
                        adr_temp = adr_reg[32:2]
                        wr_temp = write_reg
                        we_temp = we_reg
                    else:
                        adr_temp = bus.adr_o[32:2]
                        wr_temp = db_wr
                        we_temp = we_o
                    if we_o==0:
                        bus.db_rd.next = ram[adr_temp]
                    else:
                        wd=modbv(0)[32:]
                        wd[:] = ram[adr_temp]
                        for i in range(len(we_temp)):         
                           
                            if we_temp[i]:
                                low = i * 8
                                high = low+8
                                wd[high:low] = wr_temp[high:low]

                        ram[adr_temp].next = wd 

                    bus.ack_i.next = True    

        return instances()            
"""
RISC-V load/store module
(c) 2019 The Bonfire Project
License: See LICENSE
"""
from __future__ import print_function

from myhdl import *

from instructions import LoadFunct3, StoreFunct3

from util import signed_resize

write_pipe_index = 0 # Declaration 

class DbusBundle:
    """
    Simple Databus with enough features to be extended to Wishbone B4
    Can support pipelined mode, similar to Wishbone B4 pipelined mode
    """
    def __init__(self,config):
        xlen=config.xlen

        self.en_o = Signal(bool(0))
        self.we_o = Signal(modbv(0)[xlen/8:]) # Byte wide write enable signals
        self.adr_o = Signal(modbv(0)[xlen:])  # Lower log2(xlen/8) bits will always be zero
        self.stall_i=Signal(bool(0)) # When True stall pipelining, a slave not supporting piplelining can keep stall True all the time
        self.ack_i=Signal(bool(0)) # True: Data are written or ready to read on the bus, terminates cycle
        self.error_i = Signal(bool(0)) # Signals a bus error (will be raised in place of ack_i)
        self.db_wr = Signal(modbv(0)[xlen:])
        self.db_rd = Signal(modbv(0)[xlen:])



class LoadStoreBundle:
    def __init__(self,config):
        self.config = config
        xlen = config.xlen

        # Inputs
        self.store_i = Signal(bool(0)) # True: Operation is store, False: load
        self.funct3_i = Signal(modbv(0)[3:])
        self.op1_i = Signal(modbv(0)[xlen:])
        self.op2_i = Signal(modbv(0)[xlen:])
        self.displacement_i = Signal(modbv(0)[12:])
        self.rd_i = Signal(modbv(0)[5:])

        #Output
        self.result_o = Signal(modbv(0)[xlen:])
        self.rd_o = Signal(modbv(0)[5:])


        # Control Signals
        self.en_i=Signal(bool(0))
        self.busy_o=Signal(bool(0))
        self.valid_o=Signal(bool(0))

        #Execption Signals
        self.misalign_store_o = Signal(bool(0))
        self.misalign_load_o = Signal(bool(0))
        self.bus_error_o = Signal(bool(0))
        self.invalid_op_o = Signal(bool(0))

        #debug signals
        self.debug_empty=Signal(bool(0))



    @block
    def LoadStoreUnit(self,bus,clock,reset):

        """
           max_outstanding cannot larger than the minimum latency of the LSU. 
           The minimum latency is 3 cycles in case of a registered data bus read stage (config.registered_read_stage==True)
           The minimum latency is 2 cycles without a registered data bus read stage 

        """
        max_outstanding = self.config.loadstore_outstanding
        if self.config.registered_read_stage:
            assert(max_outstanding>0 and max_outstanding <=3)
        else:    
            assert(max_outstanding>0 and max_outstanding <=2)

        """
                  Write cycles will always complete combinatorical on db.ack_i, wich happens after two cylces
                  For this reason on writes the pipleline is one stage shorter.
                  The right pipeline index to use on write cycles is stored on write_pipe_index
        """
        if max_outstanding==3:
            write_pipe_index = 1
        else:
            write_pipe_index = max_outstanding-1

        max_pipe_index = max_outstanding-1
        outstanding_counter_len =  2

        outstanding = Signal(intbv(0)[outstanding_counter_len:])

        pipe_rd = [Signal(modbv(0)[5:]) for i in range(max_outstanding) ]

        pipe_adr_lo = [Signal(modbv(0)[2:]) for i in range(max_outstanding) ]

        pipe_byte_mode =  [Signal(bool(0)) for i in range(max_outstanding) ]
        pipe_hword_mode =  [Signal(bool(0)) for i in range(max_outstanding) ]
        pipe_unsigned = [Signal(bool(0)) for i in range(max_outstanding) ]

        pipe_store= [Signal(bool(0)) for i in range(max_outstanding) ]
        pipe_misalign= [Signal(bool(0)) for i in range(max_outstanding) ]
        pipe_invalid_op= [Signal(bool(0)) for i in range(max_outstanding) ]

        rdmux_out = Signal(modbv(0)[self.config.xlen:])

        valid_comb = Signal(bool(0))
       

        bus_en = Signal(bool(0))
        en_r = Signal(bool(0))
        busy = Signal(bool(0))
       

        @always_seq(clock.posedge,reset=reset)
        def drive_bus():

            invalid_op=False
           
            # Deassert en if bus is not stalled 
            if not bus.stall_i:
                bus_en.next = False

            if max_outstanding>1:           
                if (self.en_i or en_r) and not busy:
                    # Advance Pipeline 
                    for i in range(1,max_outstanding):
                        pipe_rd[i].next = pipe_rd[i-1]
                        pipe_adr_lo[i].next = pipe_adr_lo[i-1]
                        pipe_byte_mode[i].next = pipe_byte_mode[i-1]
                        pipe_hword_mode[i].next = pipe_hword_mode[i-1]
                        pipe_store[i].next = pipe_store[i-1]
                        pipe_unsigned[i].next = pipe_unsigned[i-1]
                        pipe_misalign[i].next = pipe_misalign[i-1]
                        pipe_invalid_op[i].next = pipe_invalid_op[i-1]


            if self.en_i and not busy:
              
                adr = modbv(self.op1_i + self.displacement_i.signed())[self.config.xlen:]

                byte_mode = self.funct3_i[2:] == LoadFunct3.RV32_F3_LB
                word_mode = self.funct3_i[2:] == LoadFunct3.RV32_F3_LW
                hword_mode = self.funct3_i[2:] == LoadFunct3.RV32_F3_LH
          
                invalid_op = self.funct3_i[2] and self.store_i or \
                             not ( byte_mode or word_mode or hword_mode )

                # Misalign check
                adr_lo = adr[2:]
                misalign =  hword_mode and adr_lo == 0b11 or \
                            word_mode and adr_lo != 0b00


                if not misalign:
                    #print("Start cycle:",now())
                    bus.adr_o.next = adr
                    bus_en.next = True
                    if self.store_i:
                        if word_mode:
                            bus.we_o.next = 0b1111
                        elif hword_mode:
                            bus.we_o.next = 0b0011 << adr_lo
                        elif byte_mode:
                            bus.we_o.next = 1 << adr_lo
                        else:
                            bus.we_o.next = 0

                        bus.db_wr.next = self.op2_i << adr_lo * 8 # Shift to right position on data bus
                    else: # read
                        bus.we_o.next = 0     

                if self.store_i:
                    pipe_rd[0].next=0
                else:    
                    pipe_rd[0].next = self.rd_i

                pipe_byte_mode[0].next = byte_mode
                pipe_hword_mode[0].next = hword_mode
                pipe_store[0].next = self.store_i
                pipe_unsigned[0].next = self.funct3_i[2]
                pipe_misalign[0].next = misalign
                pipe_invalid_op[0].next = invalid_op
                pipe_adr_lo[0].next = adr_lo

               
            # Cycle Termination
            if bus.ack_i or bus.error_i and outstanding > 0:
               
               
                # self.valid_o.next =  bus.ack_i and not \
                #   (pipe_misalign[max_outstanding-1] or  pipe_invalid_op[max_outstanding-1])
                self.bus_error_o.next = bus.error_i
                self.invalid_op_o.next = pipe_invalid_op[max_pipe_index]
                self.misalign_load_o.next = pipe_misalign[max_pipe_index] and not pipe_store[max_pipe_index]
                self.misalign_store_o.next =  pipe_misalign[max_pipe_index] and  pipe_store[max_pipe_index]
               
                

        @always_seq(clock.posedge,reset=reset)
        def calc_outstanding():

            next_outstanding=intbv(0)[outstanding_counter_len:]
            next_outstanding[:] = outstanding.val

            if self.en_i and not busy:
                en_r.next=True 
                next_outstanding[:] = next_outstanding + 1

            if  bus.ack_i or bus.error_i and outstanding > 0:
                next_outstanding[:] = next_outstanding - 1
                if next_outstanding == 0:
                    en_r.next=False

            outstanding.next = next_outstanding       


        # Design time code
        if max_outstanding==3:
            mux_index=1
        else:
            mux_index=max_pipe_index
        # end design time code 

        @always_comb
        def rd_mux():

            a = pipe_adr_lo[mux_index]
            pos = 0
          
            if pipe_byte_mode[mux_index]:
                pos = a * 8
                # if a == 0b00:
                #     pos = 0
                # elif a == 0b01:
                #     pos = 8
                # elif a == 0b10:
                #     pos = 16
                # elif a== 0b11:
                #     pos = 24

                if pipe_unsigned[mux_index]:
                    rdmux_out.next = bus.db_rd[pos+8:pos]
                else:
                    rdmux_out.next = signed_resize(bus.db_rd[pos+8:pos],self.config.xlen)

            elif pipe_hword_mode[mux_index]:
                if a[1]:
                    pos = 16
                else:
                    pos = 0    

                if pipe_unsigned[mux_index]:
                    rdmux_out.next = bus.db_rd[pos+16:pos]
                else:
                    rdmux_out.next = signed_resize(bus.db_rd[pos+16:pos],self.config.xlen)
            else:
                rdmux_out.next = bus.db_rd


        @always_comb
        def comb():
            l_busy =  bus.stall_i or ( outstanding == max_outstanding and not (not self.config.registered_read_stage and bus.ack_i) )
            busy.next = l_busy
            self.busy_o.next = l_busy

            self.debug_empty.next = outstanding == 0
            self.rd_o.next = pipe_rd[max_pipe_index]
            bus.en_o.next = bus_en

            valid_comb.next = bus.ack_i and not \
                             (pipe_misalign[max_pipe_index] or  pipe_invalid_op[max_pipe_index])            
                              

        if not self.config.registered_read_stage:

            @always_comb
            def ls_out():
                self.result_o.next=rdmux_out
                self.valid_o.next=valid_comb
                
        else:

            valid_reg = Signal(bool(0))

            @always_seq(clock.posedge,reset=reset)
            def ls_out():
                self.result_o.next=rdmux_out
                valid_reg.next=valid_comb
                         
            @always_comb
            def ls_valid_out():

                if pipe_store[write_pipe_index]:
                    # Writes can be terminated early 
                    self.valid_o.next = valid_comb
                else:
                    self.valid_o.next = valid_reg    


        return instances()
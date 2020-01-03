"""
RISC-V load/store module
(c) 2019 The Bonfire Project
License: See LICENSE
"""
from __future__ import print_function

from myhdl import *

from instructions import LoadFunct3, StoreFunct3


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

        max_outstanding = self.config.loadstore_outstanding
        outstanding = Signal(intbv(0,max=max_outstanding+1))

        pipe_rd = [Signal(modbv(0)[5:]) for i in range(max_outstanding) ]

        pipe_adr_lo = [Signal(modbv(0)[2:]) for i in range(max_outstanding) ]

        pipe_byte_mode =  [Signal(bool(0)) for i in range(max_outstanding) ]
        pipe_hword_mode =  [Signal(bool(0)) for i in range(max_outstanding) ]
        pipe_signed = [Signal(bool(0)) for i in range(max_outstanding) ]

        pipe_store= [Signal(bool(0)) for i in range(max_outstanding) ]
        pipe_misalign= [Signal(bool(0)) for i in range(max_outstanding) ]
        pipe_invalid_op= [Signal(bool(0)) for i in range(max_outstanding) ]

        rdmux_out = Signal(modbv(0)[self.config.xlen:])

        valid_comb = Signal(bool(0))

        bus_en = Signal(bool(0))
        en_r = Signal(bool(0))
        busy = Signal(bool(0))
       


        @always_comb
        def valid_proc():
            valid_comb.next = bus.ack_i and not \
                             (pipe_misalign[max_outstanding-1] or  pipe_invalid_op[max_outstanding-1])

        @always_seq(clock.posedge,reset=reset)
        def drive_bus():

            invalid_op=False
            next_outstanding = outstanding.val
            # Deassert en if bus is not stalled 
            if not bus.stall_i:
                bus_en.next = False

            new_request = self.en_i and not bus.stall_i

            if (new_request or en_r) and not busy:
                # Advance Pipeline 
                for i in range(1,max_outstanding):
                    pipe_rd[i].next = pipe_rd[i-1]
                    pipe_adr_lo[i].next = pipe_adr_lo[i-1]
                    pipe_byte_mode[i].next = pipe_byte_mode[i-1]
                    pipe_hword_mode[i].next = pipe_hword_mode[i-1]
                    pipe_store[i].next = pipe_store[i-1]
                    pipe_signed[i].next = pipe_signed[i-1]
                    pipe_misalign[i].next = pipe_misalign[i-1]
                    pipe_invalid_op[i].next = pipe_invalid_op[i-1]


            if new_request and not busy:
                en_r.next=True 
                adr = modbv(self.op1_i + self.displacement_i.signed())[self.config.xlen:]

                byte_mode = self.funct3_i[2:] == LoadFunct3.RV32_F3_LB
                word_mode = self.funct3_i[2:] == LoadFunct3.RV32_F3_LW
                hword_mode = self.funct3_i[2:] == LoadFunct3.RV32_F3_LH
                signed_ld = self.funct3_i[3]

                invalid_op = signed_ld and self.store_i or \
                             not ( byte_mode or word_mode or hword_mode )

                # Misalign check
                adr_lo = adr[2:]
                misalign =  hword_mode and adr_lo == 0b11 or \
                            word_mode and adr_lo != 0b00


                if not misalign:
                    print("Start cycle:",now())
                    bus.adr_o.next = adr
                    bus_en.next = True
                    if self.store_i:
                        if word_mode:
                            bus.we_o.next = 0b1111
                        elif hword_mode:
                            bus.we_o.next = 0b0011 << adr_lo
                        elif byte_mode:
                            bus.we_o.next = 2 ** adr_lo
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
                pipe_signed[0].next = signed_ld
                pipe_misalign[0].next = misalign
                pipe_invalid_op[0].next = invalid_op

                next_outstanding = next_outstanding + 1
             

            # Cycle Termination
            if bus.ack_i or bus.error_i and outstanding > 0:
               
                next_outstanding = next_outstanding - 1
                # self.valid_o.next =  bus.ack_i and not \
                #   (pipe_misalign[max_outstanding-1] or  pipe_invalid_op[max_outstanding-1])
                self.bus_error_o.next = bus.error_i
                self.invalid_op_o.next = pipe_invalid_op[max_outstanding-1]
                self.misalign_load_o.next = pipe_misalign[max_outstanding-1] and not pipe_store[max_outstanding-1]
                self.misalign_store_o.next =  pipe_misalign[max_outstanding-1] and  pipe_store[max_outstanding-1]
               
                if next_outstanding == 0:
                    bus_en.next = False
                    en_r.next=False

            outstanding.next = next_outstanding


        @always_comb
        def rd_mux():
            a = pipe_adr_lo[max_outstanding-1]
            if pipe_byte_mode[max_outstanding-1]:
                if a == 0b00:
                    byte = bus.db_rd(8,0)
                elif a == 0b01:
                    byte = bus.db_rd(16,8)
                elif a == 0b10:
                    byte = bus.db_rd(24,16)
                elif a== 0b11:
                    byte = bus.db_rd(32,24)
                if pipe_signed[max_outstanding-1]:
                    rdmux_out.next = byte.signed()
                else:
                    rdmux_out.next = byte

            elif pipe_hword_mode[max_outstanding-1]:
                if a == 0b00:
                    hword = bus.db_rd(16,0)
                elif a == 0b01:
                    hword = bus.db_rd(24,8)
                else:
                    hword = bus.db_rd(32,16)
                if pipe_signed[max_outstanding-1]:
                    rdmux_out.next = hword.signed()
                else:
                    rdmux_out.next = hword
            else:
                rdmux_out.next = bus.db_rd

        @always_comb
        def comb():
            l_busy =  outstanding == max_outstanding
            busy.next = l_busy
            self.busy_o.next = l_busy
            self.debug_empty.next = outstanding == 0
            self.rd_o.next = pipe_rd[max_outstanding-1]
            bus.en_o.next = bus_en
                              

        if self.config.loadstore_combi:

            @always_comb
            def ls_out():
                self.result_o.next=rdmux_out
                self.valid_o.next=valid_comb
                #self.rd_o.next = pipe_rd[max_outstanding-1]
        else:
            @always_seq(clock.posedge,reset=reset)
            def ls_out():
                self.result_o.next=rdmux_out
                self.valid_o.next=valid_comb
                #self.rd_o.next = pipe_rd[max_outstanding-1]         



        return instances()
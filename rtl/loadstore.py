"""
RISC-V load/store module
(c) 2019 The Bonfire Project
License: See LICENSE
"""
from __future__ import print_function

from myhdl import *

from rtl.instructions import LoadFunct3, StoreFunct3

from rtl.util import signed_resize
from rtl.barrel_shifter import left_shift_comb
from rtl.pipeline_control import *

write_pipe_index = 0 # Declaration 

from rtl.bonfire_interfaces import DbusBundle


class LoadStoreBundle(PipelineControl):
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
        self.we_o = Signal(bool(0))


        # # Control Signals
        # self.en_i=Signal(bool(0))
        # self.busy_o=Signal(bool(0))
        # self.valid_o=Signal(bool(0))

        #Execption Signals
        self.misalign_store_o = Signal(bool(0))
        self.misalign_load_o = Signal(bool(0))
        self.bus_error_o = Signal(bool(0))
        self.invalid_op_o = Signal(bool(0))

        #debug signals
        self.debug_empty=Signal(bool(0))

        PipelineControl.__init__(self)



    @block
    def LoadStoreUnit(self,bus,clock,reset):

        """
           Design time code 

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
        if max_outstanding > 1:
            outstanding_counter_len =  2
        else:
            outstanding_counter_len = 1 

        """
        End Design time code 
        """        

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

        request = Signal(bool(0))
        confirm = Signal(bool(0))

        adr = Signal(modbv(0)[self.config.xlen:])
        op2_shifted = Signal(modbv(0)[self.config.xlen:])

        """
        Use Barrel shifter to implement left shift of operand 2 for byte and hword writes
        Logic below will check for invalid (misaligned) writes 
        """
        wr_shift_instance= left_shift_comb(self.op2_i,op2_shifted,adr,0,5,3)


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


            if self.taken:
               
                byte_mode = self.funct3_i[2:] == LoadFunct3.RV32_F3_LB
                word_mode = self.funct3_i[2:] == LoadFunct3.RV32_F3_LW
                hword_mode = self.funct3_i[2:] == LoadFunct3.RV32_F3_LH
          
                invalid_op = self.funct3_i[2] and self.store_i or \
                             not ( byte_mode or word_mode or hword_mode )

                # Misalign check
               
                misalign =  hword_mode and adr[0] == True or \
                            word_mode and adr[2:0] != 0

                if not misalign:
                    #print("Start cycle:",now())
                    bus.adr_o.next = adr
                    bus_en.next = True
                    if self.store_i:
                        if word_mode:
                            bus.we_o.next = 0b1111
                        elif hword_mode:
                            if adr[1]==0: # All other cases are already excluded with the misalign check
                                bus.we_o.next = 0b0011
                            else:
                                bus.we_o.next = 0b1100     
                        elif byte_mode:
                            # convertible construct ;-)
                            if adr[2:0]==0:
                                bus.we_o.next = 0b0001
                            elif adr[2:0]==1:
                                bus.we_o.next = 0b0010
                            elif adr[2:0]==2:
                                bus.we_o.next = 0b0100
                            else:
                                bus.we_o.next = 0b1000     
                        else:
                            bus.we_o.next = 0

                        bus.db_wr.next = op2_shifted
                    else: # read
                        bus.we_o.next = 0     
                
                  
                pipe_rd[0].next = self.rd_i
                pipe_byte_mode[0].next = byte_mode
                pipe_hword_mode[0].next = hword_mode
                pipe_store[0].next = self.store_i
                pipe_unsigned[0].next = self.funct3_i[2]
                pipe_misalign[0].next = misalign
                pipe_invalid_op[0].next = invalid_op
                pipe_adr_lo[0].next = adr[2:0]


            # Cycle Termination
            if (bus.ack_i or bus.error_i) and outstanding > 0:
                # self.valid_o.next =  bus.ack_i and not \
                #   (pipe_misalign[max_outstanding-1] or  pipe_invalid_op[max_outstanding-1])
                self.bus_error_o.next = bus.error_i
                self.invalid_op_o.next = pipe_invalid_op[max_pipe_index]
                self.misalign_load_o.next = pipe_misalign[max_pipe_index] and not pipe_store[max_pipe_index]
                self.misalign_store_o.next =  pipe_misalign[max_pipe_index] and  pipe_store[max_pipe_index]


        """
        Signals new request or confirmation of existing request 
        """
        @always_comb
        def req_confirm():
            request.next =  self.taken 
            confirm.next =  ( bus.ack_i or bus.error_i ) and outstanding > 0      
                

        @always_seq(clock.posedge,reset=reset)
        def calc_outstanding():

            if request:
                en_r.next=True 
               
            if request and not confirm:
                outstanding.next = outstanding + 1
            elif not request and confirm:
                if outstanding > 0:
                    o_next = outstanding - 1  
                    outstanding.next = o_next  
                    if o_next == 0:
                        en_r.next=False


        # Design time code
        if max_outstanding==3:
            mux_index=1
        else:
            mux_index=max_pipe_index
        # end design time code 

        @always_comb
        def rd_mux():

            a = pipe_adr_lo[mux_index]
            sign = False 
          
            if pipe_byte_mode[mux_index]:

                if a==0:
                    rdmux_out.next[8:0] = bus.db_rd[8:]
                    sign = bus.db_rd[7]
                elif a==1:
                    rdmux_out.next[8:0] = bus.db_rd[16:8]
                    sign = bus.db_rd[15]
                elif a==2:
                    rdmux_out.next[8:0] = bus.db_rd[24:16]
                    sign = bus.db_rd[23]
                else:
                    rdmux_out.next[8:0] = bus.db_rd[32:24] 
                    sign = bus.db_rd[31]           
 
                for i in range(8,self.config.xlen):
                    rdmux_out.next[i] = sign and not pipe_unsigned[mux_index]

            elif pipe_hword_mode[mux_index]:

                if a[1]:
                    sign = bus.db_rd[31] and not pipe_unsigned[mux_index]
                    rdmux_out.next[16:0] = bus.db_rd[32:16]
                else:
                    sign = bus.db_rd[15] and not pipe_unsigned[mux_index]
                    rdmux_out.next[16:0] = bus.db_rd[16:0]
                
               
                for i in range(16,self.config.xlen):
                    rdmux_out.next[i] = sign    

            else:
                rdmux_out.next = bus.db_rd


        @always_comb
        def comb():

            adr.next = self.op1_i + self.displacement_i.signed()

            l_busy =  bus.stall_i or ( outstanding == max_outstanding and not (not self.config.registered_read_stage and bus.ack_i) )
            busy.next = l_busy
           

            self.debug_empty.next = outstanding == 0
            self.rd_o.next = pipe_rd[max_pipe_index]
            bus.en_o.next = bus_en

            valid_comb.next = confirm and not \
                             (pipe_misalign[max_pipe_index] or  pipe_invalid_op[max_pipe_index])            
                              

        if not self.config.registered_read_stage:

            ls_pi=self.pipeline_instance(busy,valid_comb)

            @always_comb
            def ls_out():
                self.result_o.next=rdmux_out
                self.we_o.next = not pipe_store[write_pipe_index]
                
        else:

            valid_reg = Signal(bool(0))
            valid =  Signal(bool(0))
            ext_busy = Signal(bool(0))

            ls_pi=self.pipeline_instance(ext_busy,valid)

            @always_seq(clock.posedge,reset=reset)
            def ls_out():
                self.result_o.next=rdmux_out
                valid_reg.next=valid_comb
                         
            @always_comb
            def ls_valid_out():

                if pipe_store[write_pipe_index]:
                    # Writes can be terminated early
                    if self.config.mem_write_early_term: 
                        valid.next = valid_comb
                        ext_busy.next = busy
                    else:
                        valid.next = valid_reg
                        ext_busy.next = busy  or valid_reg # Extend busy to the valid phase

                    self.we_o.next = False
                    
                else:
                    valid.next = valid_reg
                    self.we_o.next = valid_reg
                    ext_busy.next = busy  or valid_reg # Extend busy to the valid phase

                

        return instances()
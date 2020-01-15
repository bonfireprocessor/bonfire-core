"""
Barrel Shifter Library
(c) 2019 The Bonfire Project
License: See LICENSE
"""

from myhdl import *



@block
def left_shift_comb(d_i,d_o, shift_i, fill_i,c_sh_power_high=5,c_sh_power_low=0):
    """
  Parameters:
    Runtime:

        d_i     : input Signal bit vector Input Data (aribitrary length)
        d_o     : output Signal bit vector : Shiftet output, must be same length as d_i
        shift_i : bit vector, shift amount
        fill_i :  bool fill value, which is filled in from right side

    Configuration:
        c_sh_power_high : Highest bit of shift_i power of two, in python style, exluding high value
        c_sh_power_low  : Lowest bit of shift_i power of two

    Realizes a combinatorical barrel shifter. The c_sh_power_high and c_sh_power_low define the power of two values
    for the shift amount. This allows creation of cascaded barrel shifters, e.g. with pipeline stages in between.
    For example the first instance will shift the powers 0..2, the second one 3..4
    """

    l=len(d_i)
    print "Shifter instance with config {} {}".format(c_sh_power_high,c_sh_power_low)
    
    @always_comb
    def comb():
        p=c_sh_power_low
       

        temp=modbv(d_i.val)[l:]
        
        fill=intbv(0)[l:]
        for i in range(len(fill)):   
            fill[i]=fill_i 

        for i in range(c_sh_power_high-c_sh_power_low):
            shift= 2**p
            if  shift_i[i]==1:
                temp[32:] = concat(temp[l-shift:0],fill[2**p:])
            p+=1

        d_o.next=temp

    return instances()

@block 
def left_shift_pipelined(clock,reset,d_i,d_o, shift_i, fill_i,en_i,ready_o, c_pipe_stage=0):
    """
  Parameters:
    Runtime:
        clock   : Clock signal
        reset   : Reset signal

        d_i     : input Signal bit vector Input Data (aribitrary length)
        d_o     : output Signal bit vector : Shiftet output, must be same length as d_i
        shift_i : bit vector, shift amount
        fill_i  :  bool fill value, which is filled in from right side
        en_i    : Input Enable Signal
        ready_o : Output ready signal

    Configuration:
        c_pipe_stage : Position of the pipeline stage, Default=0
                       0 : No pipeline stage, the shifter is fully combinatorical, ready_o is directly connected to en_i
                       >0 : Pipeline stage at <c_pipe_stage> level of shifter, must be <= len(fill_i)
        
    """

    print len(shift_i), c_pipe_stage
    assert(c_pipe_stage<=len(shift_i) and c_pipe_stage>=0)

    if c_pipe_stage > 0:

        print  "Shifter implemented with one pipeline stage: {}:{} || {}:{} ".format(c_pipe_stage,0,len(shift_i),c_pipe_stage)

        stage_reg = Signal(modbv(0)[len(d_i):])
        stage0_out = Signal(modbv(0)[len(d_i):])

        # Signal shift_1 defined as work around for potential Vivado synthesis bug when
        # indexing a signal slice (e.g. s(5 downto 3)(i))  
        shift_1 = Signal(intbv(0)[len(shift_i)-c_pipe_stage:])

        fill_r = Signal(bool(0))
       
        stage_0=left_shift_comb(d_i,stage0_out,shift_i(c_pipe_stage,0),fill_i,c_pipe_stage,0)
        stage_1=left_shift_comb(stage_reg,d_o,shift_1,fill_r,len(shift_i),c_pipe_stage)

        # @always_comb
        # def comb():
        #     shift_1.next=shift_i[len(shift_i):c_pipe_stage]


        @always_seq(clock.posedge,reset=reset)
        def shifter_pipe():
            if en_i:
                shift_1.next=shift_i[len(shift_i):c_pipe_stage]
                fill_r.next = fill_i
                stage_reg.next=stage0_out
            ready_o.next=en_i

    else:

      print "Shifter implemented without pipeline stage "  
      shifter_inst=left_shift_comb(d_i,d_o,shift_i,fill_i,len(shift_i))

      @always_comb
      def shifter():
          ready_o.next=en_i  

    return instances()


@block 
def shift_pipelined(clock,reset,d_i,d_o, shift_i, right_i, fill_i,en_i,ready_o, c_pipe_stage=0):
    """
  Parameters:
    Runtime:
        clock   : Clock signal
        reset   : Reset signal

        d_i     : input Signal bit vector Input Data (aribitrary length)
        d_o     : output Signal bit vector : Shiftet output, must be same length as d_i
        shift_i : bit vector, shift amount
        right_i : bool: True = right shift, else left shift  
        fill_i  :  bool fill value, which is filled in from right side
        en_i    : Input Enable Signal
        ready_o : Output ready signal

    Configuration:
        c_pipe_stage : Position of the pipeline stage, Default=0
                       0 : No pipeline stage, the shifter is fully combinatorical, ready_o is directly connected to en_i
                       >0 : Pipeline stage at <c_pipe_stage> level of shifter, must be <= len(fill_i)
        
    """
   
    temp_out = Signal(modbv(0)[len(d_i):])
    temp_in = Signal(modbv(0)[len(d_i):])
    right_r = Signal(bool(0))


    barrel_inst=left_shift_pipelined(clock,reset,temp_in,temp_out, shift_i, fill_i,en_i,ready_o,c_pipe_stage) 

    def reverse(d):
        r = modbv(0)[len(d_i):]
        for i in range(len(d)):
            r[len(d)-i-1] = d[i]
        return r 

    @always_seq(clock.posedge,reset=reset)
    def seq():
        right_r.next =right_i


    @always_comb
    def comb():
        if right_i:
            temp_in.next=reverse(d_i)
        else:
            temp_in.next=d_i
            
        if right_r:
            d_o.next=reverse(temp_out)
        else:
            d_o.next=temp_out


    return instances()
        
            


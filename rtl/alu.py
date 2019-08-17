"""
RISC-V ALU
(c) 2019 The Bonfire Project
License: See LICENSE
"""

from myhdl import *

from barrel_shifter import shift_pipelined

# Constants
c_add = 0b000
c_sll = 0b001
c_slt = 0b010
c_sltu = 0b011
c_xor  = 0b100
c_sr  =  0b101
c_or  =  0b110
c_and =  0b111

class AluBundle:
    def __init__(self,xlen=32):
        self.funct3_i=Signal(intbv(0)[3:])
        self.funct7_6_i=Signal(bool(0))
        self.op1_i=Signal(modbv(0)[xlen:])
        self.op2_i=Signal(modbv(0)[xlen:])
        self.res_o=Signal(modbv(0)[xlen:])
        # Control Signals
        self.en_i=Signal(bool(0))
        self.busy_o=Signal(bool(0))
        self.valid_o=Signal(bool(0))

        # Constants
        self.xlen = xlen 
    


    @block 
    def alu(self,clock,reset, c_shifter_mode="none"):
        """
          c_shifter_mode:
            "none" : Don't implement shifts
            "comb" : Single cycle barrel shifter
            "pipelined" : 2-cycle barrel shifter 
            "behavioral" : Implement shift with Python operators 
        """

        assert ( c_shifter_mode=="none" or c_shifter_mode=="comb" or c_shifter_mode=="pipelined" or c_shifter_mode=="behavioral")
        #assert ( c_shifter_mode=="none" or c_shifter_mode=="behavioral")

        shifter_out = Signal(modbv(0)[self.xlen:])
        shift_valid = Signal(bool(0))  
        shift_busy = Signal(bool(0))

        alu_valid = Signal(bool(0))

        if c_shifter_mode=="behavioral":

            @always_comb
            def shift():
                if self.funct3_i==c_sll:
                    shifter_out.next = self.op1_i << self.op2_i[5:]
                    shift_valid.next=True 
                elif self.funct3_i==c_sr:
                    shifter_out.next =  ( self.op1_i.signed() if self.funct7_6_i else self.op1_i ) >>  self.op2_i[5:]
                    shift_valid.next=True 
                else:
                     shift_valid.next=False      

        elif c_shifter_mode=="comb" or c_shifter_mode=="pipelined":
            
           
            fill_v = Signal(bool(0))
            shift_en = Signal(bool(0))
            shift_ready = Signal(bool(0))
            shift_right = Signal(bool(0))

           
            
            shift_inst=shift_pipelined(clock,reset,self.op1_i,shifter_out,self.op2_i(5,0), \
                       shift_right,fill_v,shift_en,shift_ready, 3 if c_shifter_mode=="pipelined" else 0 )

            @always_comb
            def shift_comb():
                
                shift_valid.next=shift_ready 

                
                if self.funct3_i==c_sll:
                    shift_right.next=False 
                    fill_v.next=False
                    shift_en.next=not shift_busy and self.en_i
                elif self.funct3_i==c_sr:
                    shift_right.next=True 
                    fill_v.next=self.funct7_6_i and self.op1_i[self.xlen-1]
                    shift_en.next=not shift_busy and self.en_i
                else:
                   shift_right.next=False 
                   fill_v.next=False
                   shift_en.next=False 

            if c_shifter_mode=="pipelined":
                # @always_comb
                # def shift_pipelined_comb():
                #     shift_busy.next = shift_en and not shift_valid 

                @always_seq(clock.posedge,reset=reset)
                def busy_proc():

                    if shift_busy:
                        shift_busy.next= not shift_ready
                    else:
                        shift_busy.next = shift_en

  
                   
       
        @always_comb
        def comb():

            alu_valid.next=False 

            if self.funct3_i==c_add:
                if self.funct7_6_i:
                    self.res_o.next = self.op1_i - self.op2_i
                else:
                    self.res_o.next = self.op1_i + self.op2_i      
                alu_valid.next=self.en_i 
            elif self.funct3_i==c_or:
                self.res_o.next = self.op1_i | self.op2_i 
                alu_valid.next=self.en_i 
            elif self.funct3_i==c_and:
                self.res_o.next = self.op1_i & self.op2_i
                alu_valid.next=self.en_i 
            elif self.funct3_i==c_xor:
                self.res_o.next = self.op1_i ^ self.op2_i  
                alu_valid.next=self.en_i 
            elif self.funct3_i==c_slt:
                self.res_o.next =  concat( modbv(0)[31:], self.op1_i.signed() < self.op2_i.signed() )
                alu_valid.next=self.en_i 
            elif self.funct3_i==c_sltu:
                self.res_o.next =  concat( modbv(0)[31:], self.op1_i < self.op2_i )
                alu_valid.next=self.en_i      
            elif self.funct3_i==c_sll or self.funct3_i==c_sr:
                self.res_o.next = shifter_out.val 
            else:
                assert False, "Invalid funct3_i"
                self.res_o.next = 0           


        @always_comb
        def pipe_control():
            self.valid_o.next= alu_valid or shift_valid   
            self.busy_o.next = shift_busy         
    

        return instances()         





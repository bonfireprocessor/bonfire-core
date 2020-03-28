"""
RISC-V ALU
(c) 2019 The Bonfire Project
License: See LICENSE
"""

from myhdl import *

from rtl.barrel_shifter import shift_pipelined
from rtl.instructions import ArithmeticFunct3  as f3 


class AluBundle:
    def __init__(self,xlen=32):
        # ALU Inputs
        self.funct3_i = Signal(modbv(0)[3:])
        self.funct7_6_i = Signal(bool(0))
       
        self.op1_i = Signal(modbv(0)[xlen:])
        self.op2_i = Signal(modbv(0)[xlen:])

        # ALU Outputs
        self.res_o = Signal(modbv(0)[xlen:])
        self.flag_ge = Signal(bool(0)) # Only valid when ALU is subtracting : op1>=op2 (signed)
        self.flag_uge = Signal(bool(0)) # Only valid when when ALU is subtracting : op1>=op2 (unsigned)
        self.flag_equal = Signal(bool(0)) # op1==op2 
        
        # Control Signals
        self.en_i=Signal(bool(0))
        self.busy_o=Signal(bool(0))
        self.valid_o=Signal(bool(0))

        # Constants
        self.xlen = xlen


    @block
    def adder(self,subtract_i,result_o,ge_o,uge_o):
        """
        subrtact_i : bool     do subtract
        result_o : modbv[32:] add/subtract result
        ge_o : bool    output signed greater or equal
        uge_o : bool   output, unsgined greater or equal
        """

        res = Signal(modbv(0)[self.xlen+1:]) ## accomodate for carry bit

        @always_comb
        def do_add(): 
            op_b = modbv(0)[self.xlen:]

            if subtract_i: 
                op_b[:] = ~self.op2_i
            else:
                op_b[:] = self.op2_i

            # for i in range(self.xlen):
            #     op_b[i] = self.op2_i[i] ^ subtract_i 

            res.next = self.op1_i + op_b + subtract_i

        @always_comb
        def adder_output():
            result_o.next = res[self.xlen:]
            carry = res[len(res)-1]
            s1 = self.op1_i[len(self.op1_i)-1]
            s2 = self.op2_i[len(self.op2_i)-1]
            uge_o.next = carry
            ge_o.next = (s1 and s2 and carry) or (not s1 and not s2 and carry ) or ( not s1 and s2 )

        return instances()


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

        # Adder interface
        subtract = Signal(bool(0))
        adder_out = Signal(modbv(0)[self.xlen:])
        flag_ge = Signal(bool(0))
        flag_uge = Signal(bool(0))

        add_inst=self.adder(subtract,adder_out,flag_ge,flag_uge)


        if c_shifter_mode=="behavioral":

            @always_comb
            def shift():
                if self.funct3_i==f3.RV32_F3_SLL:
                    shifter_out.next = self.op1_i << self.op2_i[5:]
                    shift_valid.next=True
                elif self.funct3_i==f3.RV32_F3_SRL_SRA:
                    shifter_out.next =  ( self.op1_i.signed() if self.funct7_6_i else self.op1_i ) >>  self.op2_i[5:]
                    shift_valid.next=True
                else:
                     shift_valid.next=False

        elif c_shifter_mode=="comb" or c_shifter_mode=="pipelined":


            fill_v = Signal(bool(0))
            shift_en = Signal(bool(0))
            shift_ready = Signal(bool(0))
            shift_right = Signal(bool(0))

            shift_amount=Signal(intbv(0)[5:])

            shift_inst=shift_pipelined(clock,reset,self.op1_i,shifter_out,shift_amount, \
                       shift_right,fill_v,shift_en,shift_ready, 3 if c_shifter_mode=="pipelined" else 0 )
                      

            @always_comb
            def shift_comb():

                shift_valid.next = shift_ready
                shift_amount.next = self.op2_i[5:0]

                if self.funct3_i==f3.RV32_F3_SLL:
                    shift_right.next=False
                    fill_v.next = False
                    shift_en.next = self.en_i
                elif self.funct3_i==f3.RV32_F3_SRL_SRA:
                    shift_right.next = True
                    fill_v.next = self.funct7_6_i and self.op1_i[self.xlen-1]
                    shift_en.next = self.en_i
                else:
                   shift_right.next = False
                   fill_v.next = False
                   shift_en.next = False

            if c_shifter_mode=="pipelined":
                @always_comb
                def shift_pipelined_comb():
                    shift_busy.next = shift_en and not shift_ready

        @always_comb
        def set_subtract():
            """
            The only case the ALU is not subtracting is when there is really an add instruction
            """
            subtract.next = not (self.en_i and self.funct3_i==f3.RV32_F3_ADD_SUB and not self.funct7_6_i)

        @always_comb
        def comb():

            alu_valid.next=False
           
            if shift_valid:
                self.res_o.next = shifter_out
                alu_valid.next = True
            elif self.funct3_i==f3.RV32_F3_ADD_SUB:
                self.res_o.next = adder_out 
                alu_valid.next = self.en_i

            elif self.funct3_i==f3.RV32_F3_OR:
                self.res_o.next = self.op1_i | self.op2_i
                alu_valid.next = self.en_i

            elif self.funct3_i==f3.RV32_F3_AND:
                self.res_o.next = self.op1_i & self.op2_i
                alu_valid.next=self.en_i

            elif self.funct3_i==f3.RV32_F3_XOR:
                self.res_o.next = self.op1_i ^ self.op2_i
                alu_valid.next=self.en_i

            elif self.funct3_i==f3.RV32_F3_SLT:
                self.res_o.next = not flag_ge
                alu_valid.next=self.en_i

            elif self.funct3_i==f3.RV32_F3_SLTU:
                self.res_o.next = not flag_uge
                alu_valid.next=self.en_i
                
            # elif not c_shifter_mode=="pipelined" and ( self.funct3_i==f3.RV32_F3_SLL or self.funct3_i==f3.RV32_F3_SRL_SRA):
            #     self.res_o.next = shifter_out.val
            #     alu_valid.next = True 
            else:
                #assert not self.en_i, "Invalid funct3_i"
                self.res_o.next = 0

            # Comparator outputs 
            self.flag_ge.next = flag_ge
            self.flag_uge.next = flag_uge
            self.flag_equal.next = self.op1_i == self.op2_i 


        @always_comb
        def valid_ctrl():
            self.valid_o.next= alu_valid
           

        @always_seq(clock.posedge,reset=reset)
        def busy_ctrl():
            self.busy_o.next = shift_busy

        return instances()





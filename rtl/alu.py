"""
RISC-V ALU
(c) 2019 The Bonfire Project
License: See LICENSE
"""

from myhdl import *

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
        self.busy_i=Signal(bool(0))
        self.valid_o=Signal(bool(0))

        # Constants
        self.xlen = xlen 
    


    @block 
    def alu(self,c_pipelined_shifter=True):

       
        @always_comb
        def comb():

            if self.funct3_i==c_add:
                if self.funct7_6_i:
                    self.res_o.next = self.op1_i - self.op2_i 
                else:
                    self.res_o.next = self.op1_i + self.op2_i      

            elif self.funct3_i==c_or:
                self.res_o.next = self.op1_i | self.op2_i 
            elif self.funct3_i==c_and:
                self.res_o.next = self.op1_i & self.op2_i  
            elif self.funct3_i==c_xor:
                self.res_o.next = self.op1_i ^ self.op2_i  
            # elif self.funct3_i==c_sll:
            #     self.res_o.next = self.op1_i << self.op2_i[5:]
            # elif self.funct3_i==c_sr:
            #     t =modbv(0)[self.xlen:]
            #     if self.funct7_6_i:
            #         t[self.xlen:] = self.op1_i.signed()
            #     else:
            #         t[self.xlen:] =  self.op1_i   

            #     self.res_o.next = t  >> self.op2_i[5:]
            else:
                self.res_o.next = 0           



        return instances()         


# Dummy Test code

alu=AluBundle()

@block
def tb():

    
    #inst=alu.alu()
    inst=AluBundle.alu(alu)

    inst.convert(hdl='VHDL',std_logic_ports=True,path='vhdl_gen')

    @instance 
    def stimulus():

        yield delay(10)
        alu.funct3_i.next=c_add
        alu.op1_i.next=5
        alu.op2_i.next=10
    
        yield alu.res_o
        print int(alu.res_o.signed())

        alu.funct7_6_i.next=True 

        yield alu.res_o

        print int(alu.res_o.signed())

        # Shift 
        alu.op2_i.next=1
        alu.funct3_i.next=c_sr
        alu.funct7_6_i.next=False 
        yield alu.res_o
        print "srl",  alu.res_o

        alu.funct7_6_i.next=True 

        yield alu.res_o
        print "sra", alu.res_o


        #assert(alu.res_o==15)
        
    return instances()


dut=tb()

dut.run_sim()


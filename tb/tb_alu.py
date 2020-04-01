from __future__ import print_function

from myhdl import *
from rtl.alu import *
from rtl.instructions import ArithmeticFunct3  as f3 
from tb.ClkDriver import *
import types


clock=Signal(bool(0))
reset = ResetSignal(0, active=1, isasync=False)

alu=AluBundle()

commands=[ \
    {"f3":f3.RV32_F3_ADD_SUB,"f7":False, "a":5,"b":10,"r":lambda a,b: a + b ,"c":"add"}, \
    {"f3":f3.RV32_F3_ADD_SUB,"f7":True,"a":5,"b":10,"r":lambda a,b: a - b,"c":"sub"}, \
    {"f3":f3.RV32_F3_OR,"f7":False,"a":0xff,"b":0xff00,"r":lambda a,b: a | b,"c":"or"}, \
    {"f3":f3.RV32_F3_AND,"f7":False,"a":0xff,"b":0xff00,"r":lambda a,b: a & b,"c":"and"}, \
    {"f3":f3.RV32_F3_XOR,"f7":False,"a":0xff,"b":0xffff,"r":lambda a,b: a ^ b,"c":"xor"}, \
    {"f3":f3.RV32_F3_SLT,"f7":False,"a":-5,"b":10,"r":1,"c":"slt"}, \
    {"f3":f3.RV32_F3_SLTU,"f7":False,"a":-5,"b":10,"r":0,"c":"sltu"}, \
    {"f3":f3.RV32_F3_SLTU,"f7":False,"a":1,"b":-1,"r":1,"c":"sltu"}, \
    {"f3":f3.RV32_F3_SLT,"f7":False,"a":1,"b":-1,"r":0,"c":"slt"}, \
    {"f3":f3.RV32_F3_SLL,"f7":False,"a":0x55,"b":8,"r": lambda a,b:  a << b,"c":"sll"}, \
    {"f3":f3.RV32_F3_SRL_SRA,"f7":True,"a":0x85000000,"b":8,"r": lambda a,b:  a.signed() >> b,"c":"sra"}, \
    {"f3":f3.RV32_F3_SRL_SRA,"f7":False,"a":0x85000000,"b":8,"r": lambda a,b:  a >> b,"c":"srl"}, \
]


@block
def tb(c_shifter_mode="behavioral",test_conversion=False):

    clk_driver= ClkDriver(clock)

    #inst=alu.alu()
    inst=AluBundle.alu(alu,clock,reset, c_shifter_mode)

    if c_shifter_mode!="behavioral" and test_conversion:
       inst.convert(hdl='VHDL',std_logic_ports=True,path='vhdl_gen', name="alu_" + c_shifter_mode )


    def test_op(cmd):
        alu.funct3_i.next=cmd["f3"]
        alu.funct7_6_i.next=cmd["f7"]
        alu.op1_i.next=cmd["a"]
        alu.op2_i.next=cmd["b"]

        alu.en_i.next=True
        yield clock.posedge
        if not alu.valid_o:
            print(cmd["c"], "pipelined")
        
        alu.en_i.next=False
        while not alu.valid_o:
            yield clock.posedge
        print ("{} {} {} result: {}".format(alu.op1_i,cmd["c"], alu.op2_i,alu.res_o))
        shouldbe=modbv(0)[32:]
        r=cmd["r"]

        if type(r) == types.FunctionType:
            shouldbe[32:] = r(alu.op1_i,alu.op2_i)
        else:
            shouldbe[32:] = r

        assert alu.res_o==shouldbe,"error, should be {}".format(shouldbe.unsigned())
      
        return


    @instance
    def stimulus():

        yield clock.posedge
        for cmd in commands:
            yield test_op(cmd)

        print( "Simulation finished")
        raise StopSimulation


    return instances()

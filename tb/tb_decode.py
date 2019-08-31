

from myhdl import *
from rtl.decode import * 
from ClkDirver import *
import types


clock=Signal(bool(0))
reset = ResetSignal(0, active=1, isasync=False)

dec=Decoder()

commands=[ \
    {"opcode":0x00000513,"source":"li a0,0"}, \
    {"opcode":0x00c586b3,"source":"add	a3,a1,a2"}
]


@block
def tb():

    clk_driver= ClkDriver(clock)

    #inst=alu.alu()
    inst=Decoder.decoder(dec,clock,reset)

    inst.convert(hdl='VHDL',std_logic_ports=True,path='vhdl_gen', name="decode" )


    def test_op(cmd):
        while  dec.busy_o:
            yield clock.posedge

        dec.word_i.next=cmd["opcode"]
        print cmd["source"], hex(cmd["opcode"])
        dec.en_i.next=True
        yield clock.posedge
        
        print dec.rs1_adr_o, dec.rs2_adr_o 
        print dec.funct3_o,dec.funct7_o,dec.alu_cmd
        print dec.op1_o,dec.op2_o,dec.rd_adr_o
        yield clock.posedge
        return 
        # alu.funct3_i.next=cmd["f3"]
        # alu.funct7_6_i.next=cmd["f7"]
        # alu.op1_i.next=cmd["a"]
        # alu.op2_i.next=cmd["b"]

        # alu.en_i.next=True
        # yield clock.posedge
        # if not alu.valid_o:
        #     print(cmd["c"], "pipelined")
        
        # alu.en_i.next=False
        # while not alu.valid_o:
        #     yield clock.posedge
        # print "{} {} {} result: {}".format(alu.op1_i,cmd["c"], alu.op2_i,alu.res_o)
        # shouldbe=modbv(0)[32:]
        # r=cmd["r"]

        # if type(r) == types.FunctionType:
        #     shouldbe[32:] = r(alu.op1_i,alu.op2_i)
        # else:
        #     shouldbe[32:] = r

        # if alu.res_o==shouldbe:
        #     print "ok"
        # else:
        #     print "error, should be",shouldbe.unsigned()

        # return


    @instance
    def stimulus():

        yield clock.posedge
        for cmd in commands:
            yield test_op(cmd)

        print "Simulation finished"
        raise StopSimulation


    return instances()

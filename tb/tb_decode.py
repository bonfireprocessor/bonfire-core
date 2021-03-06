from __future__ import print_function

from myhdl import *
from rtl.decode import *
from tb.ClkDriver import *
import types
from tb.disassemble import *


clock=Signal(bool(0))
reset = ResetSignal(0, active=1, isasync=False)

dec=DecodeBundle()

commands=[ \
    {"opcode":0x00500593,"source":"li a1,5", "t": lambda d,rs1,rs2: d.op2_o==5 and d.alu_cmd and d.funct3_onehot_o==2**0 and abi_name(d.rd_adr_o)=="a1"  } , \
    {"opcode":0x00c586b3,"source":"add a3,a1,a2", \
      "t": lambda d,rs1,rs2: abi_name(rs1)=="a1" and abi_name(rs2)=="a2" and d.alu_cmd and \
            d.funct3_onehot_o==2**0 and abi_name(d.rd_adr_o)=="a3" }, \
    {"opcode":0x00461693,"source":"slli	a3,a2,0x4", \
        "t": lambda d,rs1,rs2: d.op2_o==4 and abi_name(rs1)=="a2" and d.alu_cmd and \
            d.funct3_onehot_o==2**1 and abi_name(d.rd_adr_o)=="a3" }, \
    {"opcode":0xfec588e3,"source":"beq	a1,a2,0 <_start>", "current_ip": 16, \
         "t": lambda d,rs1,rs2: abi_name(rs1)=="a1" and abi_name(rs2)=="a2" and d.branch_cmd and \
            d.funct3_onehot_o==2**0 and d.jump_dest_o == 0 }
]


@block
def tb(test_conversion=False):

    clk_driver= ClkDriver(clock)

    inst=DecodeBundle.decoder(dec,clock,reset)

    if test_conversion:
        inst.convert(hdl='VHDL',std_logic_ports=True,path='vhdl_gen', name="decode" )

    cmd_index = Signal(intbv(0))

    rs1 = Signal(intbv(0)[5:]) 
    rs2 = Signal(intbv(0)[5:])  

    @always_seq(clock.posedge,reset=reset)
    def decode_output():

        # Save register addresses
        if dec.en_i:
            rs1.next = dec.rs1_adr_o
            rs2.next = dec.rs2_adr_o 

        if dec.valid_o:
            
            if cmd_index >= len(commands):
                print ("Simulation finished")
                raise StopSimulation

            cmd = commands[cmd_index]
            print ("{} at {} ns".format( cmd["source"], now() ))
            print ("rs1: {}, rs2: {} rd:{}".format( abi_name(rs1), abi_name(rs2),abi_name(dec.rd_adr_o) ))
            print ("funct3: {} funct7: {}".format(bin(dec.funct3_onehot_o,8),bin(dec.funct7_o,7)))
            print ("op1: {} op2: {}".format( dec.op1_o, dec.op2_o,7 ))
          
            if dec.branch_cmd:
                print ("Branch target: {}".format(hex(dec.jump_dest_o)))
          
            t=cmd["t"]
       
            if type(t) == types.FunctionType:
                if t(dec,rs1,rs2):
                    print ("OK")
                else:
                    print ("FAIL")
            print ("----")
            
            cmd_index.next = cmd_index + 1 
            
    def test_op(cmd):
      
        dec.word_i.next=cmd["opcode"]
        ip =  cmd.get("current_ip",0)
        dec.current_ip_i.next = ip
        dec.next_ip_i.next = ip + 4
       
        dec.en_i.next=True
        yield clock.posedge
                   
        return
       


    @instance
    def stimulus():

      
        for cmd in commands:
            yield test_op(cmd)
           
           

        


    return instances()

from myhdl import *

from rtl.simple_pipeline import *
from ClkDirver import *

import types
from disassemble import *


clock=Signal(bool(0))
reset = ResetSignal(0, active=1, isasync=False)


backend = SimpleBackend()

fetch = FetchInputBundle()

busy = Signal(bool(0))

result_o = Signal(intbv(0)[32:])
rd_o = Signal(intbv(0)[5:])
we_o =  Signal(bool(0))


commands=[ \
    {"opcode":0x00500593,"source":"li a1,5", "t": lambda d: d.op2_o==5 and d.alu_cmd and d.funct3_o==0 and abi_name(d.rd_adr_o)=="a1"  } , \
    {"opcode":0x00c586b3,"source":"add a3,a1,a2", \
      "t": lambda d: abi_name(d.rs1_adr_o_reg)=="a1" and abi_name(d.rs2_adr_o_reg)=="a2" and d.alu_cmd and \
           d.funct3_o==0 and abi_name(d.rd_adr_o)=="a3" }, \
    {"opcode":0x00461693,"source":"slli	a3,a2,0x4", \
        "t": lambda d: d.op2_o==4 and abi_name(d.rs1_adr_o_reg)=="a2" and d.alu_cmd and \
           d.funct3_o==1 and abi_name(d.rd_adr_o)=="a3" }
    
]

@block
def tb():

    cmd_index = Signal(intbv(0))

    clk_driver= ClkDriver(clock)
    dut = backend.backend(fetch,busy,clock,reset)
    result_o.next = backend.execute.result_o
    rd_o.next = backend.execute.rd_adr_o
    we_o.next = backend.execute.reg_we_o


    dut.convert(hdl='VHDL',std_logic_ports=False,path='vhdl_gen', name="backend" )


    @always_seq(clock.posedge,reset=reset)
    def decode_output():

        dec=backend.decode 

        if dec.valid_o:
            
            if cmd_index >= len(commands):
                print "Simulation finished"
                raise StopSimulation

            cmd = commands[cmd_index]
            print "{} at {} ns".format( cmd["source"], now() )
            print "rs1: {}, rs2: {} rd:{}".format( abi_name(dec.rs1_adr_o_reg), abi_name(dec.rs2_adr_o_reg),abi_name(dec.rd_adr_o) )
            print "funct3: {} funct7: {}".format(bin(dec.funct3_o,3),bin(dec.funct7_o,7))
            print "op1: {} op2: {}".format( dec.op1_o, dec.op2_o,7 )
            if dec.branch_cmd:
                print "Branch displacement: {}".format(int(dec.branch_displacement.signed()))
          
            t=cmd["t"]
       
            if type(t) == types.FunctionType:
                if t(dec):
                    print "OK"
                else:
                    print "FAIL"
            print "----"
            
            cmd_index.next = cmd_index + 1 


    def test_op(cmd):
      
        fetch.word_i.next=cmd["opcode"]
        fetch.next_ip_i.next  = fetch.next_ip_i + 4 
        fetch.current_ip_i.next = fetch.next_ip_i
        
        fetch.en_i.next=True
        yield clock.posedge
                   
        return        


    @instance
    def stimulus():

        for cmd in commands:
            yield test_op(cmd)

        yield clock.posedge
        print "Simulation finished"
        raise StopSimulation    


    return instances()


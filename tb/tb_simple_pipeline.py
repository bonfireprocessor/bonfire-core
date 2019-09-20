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
    {"opcode":0x00a00593,"source":"li	a1,10", "t": lambda: abi_name(rd_o)=="a1" and result_o == 10  } , \
    {"opcode":0x00500613,"source":"li a2,5", "t": lambda: abi_name(rd_o)=="a2" and result_o == 5 } , \
    {"opcode":0x00c586b3,"source":"add a3,a1,a2", "t": lambda: abi_name(rd_o)=="a3" and result_o == 15 }, \
    {"opcode":0x00469693,"source":"slli	a3,a3,0x4", "t": lambda: abi_name(rd_o)=="a3" and result_o == 0xf0 }, \
    {"opcode":0xfec588e3,"source":"beq	a1,a2,0 <_start>", "t": lambda: True }
]

@block
def tb():

    cmd_index = Signal(intbv(0))

    clk_driver= ClkDriver(clock)
    dut = backend.backend(fetch,busy,clock,reset)



    dut.convert(hdl='VHDL',std_logic_ports=False,path='vhdl_gen', name="backend" )

    @always_comb
    def tb_comb():
        result_o.next = backend.execute.result_o
        rd_o.next = backend.execute.rd_adr_o
        we_o.next = backend.execute.reg_we_o

    @always_seq(clock.posedge,reset=reset)
    def commit_check():

        if cmd_index >= len(commands):
            print "Simulation finished"
            raise StopSimulation

        if we_o:

          

            cmd = commands[cmd_index]
            print "{}: commmit to {} value {}".format( cmd["source"], abi_name(rd_o), result_o)
            t=cmd["t"]
            if type(t) == types.FunctionType:
                if t():
                    print "OK"
                else:
                    print "FAIL"
            print "----"

            cmd_index.next = cmd_index + 1


    # @always_seq(clock.posedge,reset=reset)
    # def decode_output():

    #     dec=backend.decode

    #     if dec.valid_o:

    #         if cmd_index >= len(commands):
    #             print "Simulation finished"
    #             raise StopSimulation

    #         cmd = commands[cmd_index]
    #         print "{} at {} ns".format( cmd["source"], now() )
    #         print "rs1: {}, rs2: {} rd:{}".format( abi_name(dec.rs1_adr_o_reg), abi_name(dec.rs2_adr_o_reg),abi_name(dec.rd_adr_o) )
    #         print "funct3: {} funct7: {}".format(bin(dec.funct3_o,3),bin(dec.funct7_o,7))
    #         print "op1: {} op2: {}".format( dec.op1_o, dec.op2_o,7 )
    #         if dec.branch_cmd:
    #             print "Branch displacement: {}".format(int(dec.branch_displacement.signed()))

    #         t=cmd["t"]

    #         if type(t) == types.FunctionType:
    #             if t(dec):
    #                 print "OK"
    #             else:
    #                 print "FAIL"
    #         print "----"

    #         cmd_index.next = cmd_index + 1


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
        #print "Simulation finished"
        #raise StopSimulation


    return instances()


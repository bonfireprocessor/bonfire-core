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
    {"opcode":0x00a00593,"source":"li a1,10", "t": lambda: abi_name(rd_o)=="a1" and result_o == 10  } , \
    {"opcode":0x00500613,"source":"li a2,5", "t": lambda: abi_name(rd_o)=="a2" and result_o == 5 } , \
    {"opcode":0x00c586b3,"source":"add a3,a1,a2", "t": lambda: abi_name(rd_o)=="a3" and result_o == 15 }, \
    {"opcode":0x00469713,"source":"slli	a4,a3,0x4", "t": lambda: abi_name(rd_o)=="a4" and result_o == 0xf0 }, \
    {"opcode":0x00576713,"source":"ori	a4,a4,5", "t": lambda: abi_name(rd_o)=="a4" and result_o == 0xf5 }, \
    {"opcode":0x40c00633,"source":"neg	a2,a2", "t": lambda: abi_name(rd_o)=="a2" and result_o.signed() == -5 }, \
    {"opcode":0x000627b3,"source":"sltz	a5,a2", "t": lambda: abi_name(rd_o)=="a5" and result_o == 1 }, \
    {"opcode":0x00063793,"source":"sltiu	a5,a2,0", "t": lambda: abi_name(rd_o)=="a5" and result_o == 0 }, \
    {"opcode":0x800007b7,"source":"lui a5,0x80000", "t": lambda: abi_name(rd_o)=="a5" and result_o == 0x80000000 }, \
    {"opcode":0x4187d793,"source":"srai a5,a5,0x18", "t": lambda: abi_name(rd_o)=="a5" and result_o == 0xffffff80 }, \
    {"opcode":0x00078493,"source":"mv	s1,a5", "t": lambda: abi_name(rd_o)=="s1" and result_o == 0xffffff80 }, \
    {"opcode":0xfec588e3,"source":"beq	a1,a2,0 <_start>", "t": lambda: True }
]

@block
def tb():

    cmd_index = Signal(intbv(0)[32:])

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
            print "at {}ns {}:  commmit to reg {} value {}".format(now(), cmd["source"], abi_name(rd_o), result_o)
            t=cmd["t"]
            if type(t) == types.FunctionType:
                if t():
                    print "OK"
                else:
                    print "FAIL"
            print "----"

            cmd_index.next = cmd_index + 1
        elif backend.decode.branch_cmd or backend.decode.jump_cmd:
            cmd = commands[cmd_index]
            print "at {}ns: {}".format(now(),cmd["source"])
            cmd_index.next = cmd_index + 1


    fetch_index = Signal(intbv(0))

    @always_seq(clock.posedge,reset=reset)
    def feed():

        if not backend.decode.busy_o:
            if fetch_index < len(commands):
                cmd = commands[fetch_index]
                fetch.word_i.next = cmd["opcode"]
                fetch.next_ip_i.next  = fetch_index * 4
                fetch.current_ip_i.next = fetch.next_ip_i
                fetch.en_i.next=True
                fetch_index.next = fetch_index + 1
            else:
                fetch.en_i.next=False



    return instances()


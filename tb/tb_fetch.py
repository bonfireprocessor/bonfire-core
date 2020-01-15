from myhdl import *

from rtl.simple_pipeline import *
from ClkDriver import *
from sim_ram import *

import types
from disassemble import *

from rtl import config,loadstore
from rtl.fetch import FetchUnit

ram_size = 256

ram = [Signal(modbv(0)[32:]) for ii in range(0, ram_size)]

result_o = Signal(intbv(0)[32:])
rd_o = Signal(intbv(0)[5:])
we_o =  Signal(bool(0))
jump_o =  Signal(bool(0))
jump_dest_o =  Signal(intbv(0)[32:])



commands=[ \
    {"opcode":0x00a00593,"source":"li a1,10", "t": lambda: abi_name(rd_o)=="a1" and result_o == 10  } , 
    {"opcode":0x00500613,"source":"li a2,5", "t": lambda: abi_name(rd_o)=="a2" and result_o == 5 } , \
    {"opcode":0x00c586b3,"source":"add a3,a1,a2", "t": lambda: abi_name(rd_o)=="a3" and result_o == 15 }, 
    {"opcode":0x00469713,"source":"slli	a4,a3,0x4", "t": lambda: abi_name(rd_o)=="a4" and result_o == 0xf0 }, 
    {"opcode":0x00576713,"source":"ori	a4,a4,5", "t": lambda: abi_name(rd_o)=="a4" and result_o == 0xf5 }, 
    {"opcode":0x40c00633,"source":"neg	a2,a2", "t": lambda: abi_name(rd_o)=="a2" and result_o.signed() == -5 }, 
    {"opcode":0x000627b3,"source":"sltz	a5,a2", "t": lambda: abi_name(rd_o)=="a5" and result_o == 1 }, 
    {"opcode":0x00063793,"source":"sltiu	a5,a2,0", "t": lambda: abi_name(rd_o)=="a5" and result_o == 0 }, 
    {"opcode":0x800007b7,"source":"lui a5,0x80000", "t": lambda: abi_name(rd_o)=="a5" and result_o == 0x80000000 }, 
    {"opcode":0x4187d793,"source":"srai a5,a5,0x18", "t": lambda: abi_name(rd_o)=="a5" and result_o == 0xffffff80 }, 
    {"opcode":0x00078493,"source":"mv	s1,a5", "t": lambda: abi_name(rd_o)=="s1" and result_o == 0xffffff80 }, 
    {"opcode":0xfcc58ee3,"source":"beq	a1,a2,0 <test>", "t": lambda: not jump_o },
    {"opcode":0x00000493,"source":"li	s1,0", "t": lambda: abi_name(rd_o)=="s1" and result_o ==0 }, \
    {"opcode":0xdeadc937,"source":"lui	s2,0xdeadc", "t": lambda: abi_name(rd_o)=="s2" and result_o==0xdeadc000 },
     {"opcode":0xeef90913,"source":"addi	s2,s2,-273", "t": lambda: abi_name(rd_o)=="s2" and result_o ==0xdeadbeef },
    {"opcode":0x0124a223,"source":"sw	s2,4(s1)", "t": lambda: ram[1]==0xdeadbeef }, 
    {"opcode":0x0054c583,"source":"lbu	a1,5(s1)", "t": lambda: abi_name(rd_o)=="a1" and result_o==0xbe },
    {"opcode":0xfc5ff06f,"source":"j 8 <test>", "t": lambda: abi_name(rd_o)=="zero" and result_o==0x48 and jump_o  }       
]

@block
def tb(config=config.BonfireConfig(),test_conversion=False):
    clock=Signal(bool(0))
    reset = ResetSignal(1, active=1, isasync=False)

    backend_busy = Signal(bool(0))
   
    ibus = loadstore.DbusBundle(config=config) 
    debug=DebugOutputBundle()
    out = BackendOutputBundle()
    dbus = loadstore.DbusBundle(config=config) 
    fetch_bundle = FetchInputBundle(config=config)
   
    fetch_unit = FetchUnit(config=config)
    backend = SimpleBackend(config=config)
    

    clk_driver= ClkDriver(clock)
   
    dut=fetch_unit.SimpleFetchUnit(fetch_bundle,ibus,clock,reset)

    if test_conversion:
        dut.convert(hdl='VHDL',std_logic_ports=False,path='vhdl_gen', name="backend" )


    # processor Backend
    i_backend = backend.backend(fetch_bundle,backend_busy,dbus,clock,reset,out,debug)

    # Simulated Data RAM 
   
    mem = sim_ram()
    mem.setLatency(1)
    mem_i = mem.ram_interface(ram,ibus,clock,reset)


    
    @always_comb
    def comb():
        fetch_unit.jump_dest_i.next=out.jump_dest_o
        fetch_unit.jump_i.next = out.jump_o
        fetch_unit.stall_i.next = backend_busy

        result_o.next =debug.result_o
        rd_o.next = debug.rd_adr_o
        we_o.next = debug.reg_we_o
        jump_o.next = out.jump_o
        jump_dest_o.next = out.jump_dest_o


    @always_seq(clock.posedge,reset=reset)
    def sim_observe():

        if out.jump_o:
            raise StopSimulation   


    cmd_index = Signal(intbv(0))

    def check(cmd):
        t=cmd["t"]
        if type(t) == types.FunctionType:
            if t():
                print "OK"
            else:
                print "FAIL"
        print "----"


    @always_seq(clock.posedge,reset=reset)
    def commit_check():

        if cmd_index >= len(commands):
            print "Simulation finished"
            raise StopSimulation

        if debug.valid_o:
           
            cmd = commands[cmd_index]
            if debug.reg_we_o:
                print "at {}ns {}:  commmit to reg {} value {}".format(now(), cmd["source"], 
                abi_name(debug.rd_adr_o), debug.result_o)
            else:
                print "at {}ns {}:  commmit without reg write".format(now(), cmd["source"])    
            check(cmd)

            cmd_index.next = cmd_index + 1
        elif backend.decode.branch_cmd or backend.decode.jump_cmd or backend.decode.jumpr_cmd:
            cmd = commands[cmd_index]
            print "at {}ns: {}, do: {}, destination: {}".format(now(),cmd["source"],out.jump_o, out.jump_dest_o )
            check(cmd)
            cmd_index.next = cmd_index + 1


    @instance
    def stimulus():
         # Copy code to RAM
        i=0
        for cmd in commands:
            ram[i].next=cmd["opcode"]
            i += 1
        for i in range(1,5):    
            yield clock.posedge

        reset.next=0



    return instances()


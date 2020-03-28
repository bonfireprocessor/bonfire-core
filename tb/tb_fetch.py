from __future__ import print_function

from myhdl import *

from rtl.simple_pipeline import *
from tb.ClkDriver import *
from tb.sim_ram import *

import types
from tb.disassemble import *

from rtl import config,loadstore
from rtl.fetch import FetchUnit
from rtl.bonfire_interfaces import DbusBundle

ram_size = 256

code_ram = [Signal(modbv(0)[32:]) for ii in range(0, ram_size)]
data_ram = [Signal(modbv(0)[32:]) for ii in range(0, ram_size)]

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
    {"opcode":0x40c00733,"source":"neg	a4,a2", "t": lambda: abi_name(rd_o)=="a4" and result_o.signed() == -5 }, 
    {"opcode":0x000727b3,"source":"sltz	a5,a4", "t": lambda: abi_name(rd_o)=="a5" and result_o == 1 }, 
    {"opcode":0x00073793,"source":"sltiu a5,a4,0", "t": lambda: abi_name(rd_o)=="a5" and result_o == 0 }, 
    {"opcode":0x800007b7,"source":"lui a5,0x80000", "t": lambda: abi_name(rd_o)=="a5" and result_o == 0x80000000 }, 
    {"opcode":0x4187d793,"source":"srai a5,a5,0x18", "t": lambda: abi_name(rd_o)=="a5" and result_o == 0xffffff80 }, 
    {"opcode":0x00078493,"source":"mv	s1,a5", "t": lambda: abi_name(rd_o)=="s1" and result_o == 0xffffff80 }, 
    {"opcode":0xfcc58ee3,"source":"beq	a1,a2,0 <test>", "t": lambda: not jump_o },
    {"opcode":0x00000493,"source":"li	s1,0", "t": lambda: abi_name(rd_o)=="s1" and result_o ==0 }, \
    {"opcode":0xdeadc937,"source":"lui	s2,0xdeadc", "t": lambda: abi_name(rd_o)=="s2" and result_o==0xdeadc000 },
     {"opcode":0xeef90913,"source":"addi	s2,s2,-273", "t": lambda: abi_name(rd_o)=="s2" and result_o ==0xdeadbeef },
    {"opcode":0x0124a223,"source":"sw	s2,4(s1)", "t": lambda: data_ram[1]==0xdeadbeef }, 
    {"opcode":0x0054c303,"source":"lbu	t1,5(s1)", "t": lambda: abi_name(rd_o)=="t1" and result_o==0xbe },
    {"opcode":0xfc5ff06f,"source":"j 8 <test>", "t": lambda: abi_name(rd_o)=="zero" and result_o==0x48 and jump_o  },
    {"opcode":0x00100593,"source":"li a1,1", "t": lambda: False  }, # should not be executed        
]

@block
def tb(config=config.BonfireConfig(),test_conversion=False):
    clock=Signal(bool(0))
    reset = ResetSignal(1, active=1, isasync=False)

   
    ibus = DbusBundle(config=config,readOnly=True) 
    debug=DebugOutputBundle()
    out = BackendOutputBundle()
    dbus = DbusBundle(config=config) 
    fetch_bundle = FetchInputBundle(config=config)
   
    fetch_unit = FetchUnit(config=config)
    backend = SimpleBackend(config=config)
    

    clk_driver= ClkDriver(clock)
   
    dut=fetch_unit.SimpleFetchUnit(fetch_bundle,ibus,clock,reset)

    if test_conversion:
        dut.convert(hdl='VHDL',std_logic_ports=False,path='vhdl_gen', name="fetch" )


    # processor Backend
    i_backend = backend.backend(fetch_bundle,dbus,clock,reset,out,debug)

    # Simulated Code RAM 
   
    c_mem = sim_ram()
    c_mem.setLatency(1)
    c_mem_i = c_mem.ram_interface(code_ram,ibus,clock,reset,readOnly=True)

    # Simulated Data RAM
    d_mem = sim_ram()
    d_mem.setLatency(1)
    d_mem_i = d_mem.ram_interface(data_ram,dbus,clock,reset)

    
    @always_comb
    def comb():
        fetch_unit.jump_dest_i.next=out.jump_dest_o
        fetch_unit.jump_i.next = out.jump_o
        fetch_unit.stall_i.next = out.busy_o

        result_o.next =debug.result_o
        rd_o.next = debug.rd_adr_o
        we_o.next = debug.reg_we_o
        jump_o.next = out.jump_o
        jump_dest_o.next = out.jump_dest_o


    current_ip_r = Signal(intbv(0))
  
    @always_seq(clock.posedge,reset=reset)
    def sim_observe():

        if backend.execute.taken:
            t_ip = backend.decode.debug_current_ip_o
            print("@{}ns exc: {} : {} ".format(now(),t_ip,backend.decode.debug_word_o))
            assert code_ram[t_ip>>2]==backend.decode.debug_word_o, "pc vs ram content mismatch" 
            assert backend.decode.next_ip_o == t_ip + 4, "next_ip vs. current_ip mismatch" 
            current_ip_r.next = t_ip >> 2
          
        # if out.jump_o:
        #     raise StopSimulation   


   
    jump_cnt = Signal(intbv(0))

    def check(cmd):
        t=cmd["t"]
        if type(t) == types.FunctionType:
            if t():
                print("OK")
            else:
                print("FAIL")
                raise StopSimulation
        print("----")


    @always_seq(clock.posedge,reset=reset)
    def commit_check():

        if jump_cnt > 1:
            print("Simulation finished")
            raise StopSimulation

        if backend.execute.taken:
            idx = backend.decode.debug_current_ip_o >> 2
        else:
            idx = current_ip_r

        if debug.valid_o:    
            cmd = commands[ idx]
            if debug.reg_we_o:
                print("@{}ns {}:  commmit to reg {} value {}".format(now(), cmd["source"], 
                abi_name(debug.rd_adr_o), debug.result_o))
            else:
                print("@{}ns {}:  commmit without reg write".format(now(), cmd["source"]))    
            check(cmd)

            #cmd_index.next = cmd_index + 1
        if backend.execute.debug_exec_jump:
            cmd = commands[idx]
            print("at {}ns: {}, do: {}, destination: {}".format(now(),cmd["source"],out.jump_o, out.jump_dest_o ))
            check(cmd)
            #cmd_index.next = cmd_index + 1
            if out.jump_o:
                jump_cnt.next = jump_cnt + 1


    @instance
    def stimulus():
         # Copy code to RAM
        i=0
        for cmd in commands:
            code_ram[i].next=cmd["opcode"]
            i += 1
        for i in range(1,3):    
            yield clock.posedge

        reset.next=0



    return instances()


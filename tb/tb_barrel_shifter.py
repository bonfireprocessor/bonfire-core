from myhdl import *
from rtl import barrel_shifter
from tb.ClkDriver import *

d_in=Signal(intbv(1)[32:])
d_o=Signal(intbv(0)[32:])

shift_in=Signal(intbv(0)[5:])
fill_i=Signal(bool(0)) 

clock=Signal(bool(0))
reset = ResetSignal(0, active=1, isasync=False)

en_i = Signal(bool(0))
ready_o = Signal(bool(0))

@block
def tb_barrel_left_shift_comb():

    

    dut=barrel_shifter.left_shift_comb(d_in,d_o,shift_in,fill_i)

    dut.convert(hdl='VHDL',std_logic_ports=True,path='vhdl_gen')

    @instance
    def stimulus():
        print("zero fill")
       
        fill_i.next=0
        for i in range(shift_in.max):
            shift_in.next=i
            yield delay(10)
            print (i, bin(d_o,32)) 
            assert(d_o == d_in << i)
            yield delay(10)
            

        fill_i.next=True
        print("1 fill")
        for i in range(shift_in.max):
            shift_in.next=i
            yield delay(10)
            print(i, bin(d_o,32))
            fill=2**i -1
            assert(d_o == (d_in << i | fill )) 
            yield delay(10)
           
        print("finish")

    return instances()

@block 
def tb_barrel_left_shift_pipelined():

    
    clk_driver= ClkDriver(clock)

    dut=barrel_shifter.left_shift_pipelined(clock,reset,d_in,d_o,shift_in,fill_i,en_i,ready_o,3)
    dut.convert(hdl='VHDL',std_logic_ports=True,path='vhdl_gen')

    @instance
    def stimulus():

        reset.next=True
        yield delay(40)
        reset.next=False
        yield delay(40)

        print("zero fill")
       
        fill_i.next=0
        for i in range(shift_in.max):
            shift_in.next=i

            en_i.next=1
            yield clock.posedge
            en_i.next=0 

            while ready_o==0: 
                yield clock.posedge 
             
            print(i, bin(d_o,32) )
            assert(d_o == d_in << i)
            yield clock.posedge

        print("Simulation finished")
        raise StopSimulation 

    return instances()

@block 
def tb_barrel_shift_pipelined():

    
    clk_driver= ClkDriver(clock)
    shift_right = Signal(bool(0))

    dut=barrel_shifter.shift_pipelined(clock,reset,d_in,d_o,shift_in,shift_right,fill_i,en_i,ready_o,3)
    dut.convert(hdl='VHDL',std_logic_ports=True,path='vhdl_gen')

    @instance
    def stimulus():

        reset.next=True
        yield delay(40)
        reset.next=False
        yield delay(40)

        print("zero fill")
       
        fill_i.next=0
        for i in range(shift_in.max):
            shift_in.next=i

            en_i.next=1
            yield clock.posedge
            en_i.next=0 

            while ready_o==0: 
                yield clock.posedge 
             
            print (i, bin(d_o,32) )
            assert(d_o == d_in << i)
            yield clock.posedge

        print("Right shift logical")
        d_in.next=0x80000000
        shift_right.next=True
        for i in range(shift_in.max):
            shift_in.next=i

            en_i.next=1
            yield clock.posedge
            en_i.next=0 

            while ready_o==0: 
                yield clock.posedge 
             
            print(i, bin(d_o,32) )
            assert(d_o == d_in >> i)
            yield clock.posedge    

        print("Simulation finished")
        raise StopSimulation 

    return instances()    
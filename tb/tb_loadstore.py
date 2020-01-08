from __future__ import print_function

from myhdl import *

from rtl.loadstore import *
from ClkDriver import *

from rtl.instructions import LoadFunct3, StoreFunct3
from rtl import config

ram_size=256

store_words= (0xdeadbeef,0x55aaeeff,0x12345678,0x705A8000,0xaabbccdd)

ram_latency = 1 



@block
def tb(config=config.BonfireConfig(),test_conversion=False):

    print("Testing LSU with loadstore_outstanding={}, registered_read_stage={} ".format(config.loadstore_outstanding,config.registered_read_stage))
    clock=Signal(bool(0))
    reset = ResetSignal(0, active=1, isasync=False)

    clk_driver= ClkDriver(clock)

   
    bus = DbusBundle(config)
    ls = LoadStoreBundle(config)

    dut=LoadStoreBundle.LoadStoreUnit(ls,bus,clock,reset)

    if test_conversion:
        dut.convert(hdl='VHDL',std_logic_ports=False,path='vhdl_gen', name="loadstore" )


    ram = [Signal(modbv(0)[32:]) for ii in range(0, ram_size)]

    cnt = Signal(intbv(0))

    # Signal for simulating wait state logic 
    wait_states = Signal(intbv(0))
    adr_reg = Signal(modbv(0)[32:0])
    write_reg = Signal(modbv(0)[32:0])
    we_reg = Signal(modbv(0)[4:])
   
    @always_comb
    def bus_stall():
        if ram_latency>1:
            bus.stall_i.next = bus.en_o and wait_states>0
        else:
            bus.stall_i.next = False     

    @always_seq(clock.posedge,reset=reset)
    def bus_slave():

        bus.ack_i.next=False

        must_wait = ram_latency > 1

        if bus.en_o and must_wait and wait_states==0:
            wait_states.next = ram_latency-1
            adr_reg.next = bus.adr_o
            write_reg.next = bus.db_wr
            we_reg.next = bus.we_o
            
        elif ( not must_wait and bus.en_o ) or wait_states != 0:

            if must_wait: 
                w = wait_states - 1
                wait_states.next = w
            else:
                w = 0    

            if w==0: # When all wait states consumed ack bus cycle
                if must_wait:
                    adr_temp = adr_reg[32:2]
                    wr_temp = write_reg
                    we_temp = we_reg
                else:
                    adr_temp = bus.adr_o[32:2]
                    wr_temp = bus.db_wr
                    we_temp = bus.we_o
                if bus.we_o==0:
                    bus.db_rd.next = ram[adr_temp]
                else:
                    wd=modbv(0)[32:]
                    wd[:] = ram[adr_temp]
                    for i in range(len(we_temp)):         
                       
                        if we_temp[i]:
                            low = i * 8
                            high = low+8
                            wd[high:low] = wr_temp[high:low]

                    ram[adr_temp].next = wd 

                bus.ack_i.next = True    
           
          
    
    fetch_index = Signal(intbv(0))
    
    def sw_test():
        fetch_index.next = 0
        yield clock.posedge

        ls.funct3_i.next = StoreFunct3.RV32_F3_SW
        ls.store_i.next = True
        ls.op1_i.next = 0
        ls.rd_i.next = 5

        countdown=len(store_words)

        while countdown>0:

            if ls.valid_o:
                countdown -= 1

            if fetch_index<len(store_words):
                ls.en_i.next = True
                if not ls.busy_o:
                    ls.displacement_i.next = fetch_index * 4
                    ls.op2_i.next = store_words[fetch_index]
                    fetch_index.next += 1

            else:
                if not ls.busy_o:   
                    ls.en_i.next=False    

            yield clock.posedge

        # Verify memory content 
        i=0
        for v in store_words:
            print("write check ram[{}]: {}=={} ".format(i,ram[i],hex(v)))
            assert ram[i]==v, "loadstore sw test failed"
            i += 1

   

    def lw_test():
        yield clock.posedge
        ls.funct3_i.next = LoadFunct3.RV32_F3_LW
        ls.store_i.next= False
        ls.op1_i.next=0
       
        count=len(store_words)
        finish=False
        i=Signal(intbv(0))

        while not finish:
            if not ls.busy_o:
                ls.displacement_i.next= i*4
                ls.rd_i.next= i # "Misuse" rd register as index into test data
                i.next +=  1
                ls.en_i.next = i<count 
                
                if ls.valid_o:
                    print("read check x{}: {} == {}".format(ls.rd_o,ls.result_o,hex(store_words[ls.rd_o])))
                    assert(ls.result_o==store_words[ls.rd_o]), "loadstore lw test failed"
                    finish = ls.rd_o==count-1
            
            yield clock.posedge            


    def sb_test():
        yield clock.posedge
        ls.funct3_i.next = StoreFunct3.RV32_F3_SB
        ls.store_i.next = True
        ls.op1_i.next = 5<<2 # Base Memory address for test
        ls.rd_i.next = 5

        countdown=8
        displacement=0

        while countdown>0:

            if ls.valid_o:
                countdown -=  1

            if displacement<8:
                ls.en_i.next = True
                if not ls.busy_o:
                    ls.displacement_i.next = displacement
                    # Extract next byte from store_words 
                    ls.op2_i.next = store_words[displacement>>2] >> (displacement % 4* 8)
                    displacement += 1

            else:
                if not ls.busy_o:   
                    ls.en_i.next=False    

            yield clock.posedge

        print("Store Byte result: {} {}".format(ram[5],ram[6]))
        assert (ram[5]==store_words[0] and ram[6]==store_words[1]), "loadstore sb test failed"


    def sh_test():
        yield clock.posedge
        ls.funct3_i.next = StoreFunct3.RV32_F3_SH
        ls.store_i.next = True
        ls.op1_i.next = 7<<2 # Base Memory address for test
        ls.rd_i.next = 5

        countdown=4
        displacement=0

        while countdown>0:

            if ls.valid_o:
                countdown -= 1

            if displacement<8:
                ls.en_i.next = True
                if not ls.busy_o:
                    ls.displacement_i.next = displacement
                    # Extract next half word from store_words 
                    ls.op2_i.next = store_words[displacement>>2] >> ((displacement >> 1 & 1)  * 16)
                    displacement +=  2

            else:
                if not ls.busy_o:   
                    ls.en_i.next=False    

            yield clock.posedge

        print("Store word result: {} {}".format(ram[7],ram[8]))
        assert(ram[7]==store_words[0] and ram[8]==store_words[1]), "loadstore sh test failed"


    def load_single(base,displacement,funct3): 
        ls.funct3_i.next = funct3
        ls.store_i.next = False
        ls.op1_i.next = base 
        ls.rd_i.next = 5
        ls.displacement_i.next = displacement
        ls.en_i.next = True
        yield clock.posedge
        while ls.busy_o:
            yield clock.posedge
        ls.en_i.next = False 

        while not ls.valid_o:
            yield clock.posedge
        print(now())

    def wait_valid():
         while ls.valid_o:
           yield clock.posedge

       

    def _check(a,b,message):
       s= "{}: checking {}=={}".format(message,hex(a),hex(b))
       assert a==b, s + " failed"
       print(s," OK")


    def load_other_test():
        """
        Test lb,lbu,lh,lhu
        """
        assert ram[3]==0x705a8000, "load_other:  ram[3] does not contain the expected content"
        yield clock.posedge

        print("Testing lbu")
        yield load_single(3<<2,1,LoadFunct3.RV32_F3_LBU) ## Should read the ff byte 
        _check(ls.result_o,0x80,"lbu test" )
       
        print("Testing lb negative")
        yield load_single(3<<2,1,LoadFunct3.RV32_F3_LB) ## Should read and sign extend the ff byte 
        _check(ls.result_o,0xffffff80,"lb negative test" )
       
        print("Testing lb positive")
        yield load_single(3<<2,2,LoadFunct3.RV32_F3_LB) ## Should read and sign extend the 55 byte 
        _check(ls.result_o,0x5a,"lb positive test" )

        print("Testing lhu")
        yield load_single(3<<2,0,LoadFunct3.RV32_F3_LHU) ## Should read the ff00 hword 
        _check(ls.result_o,0x8000,"lhu test" )

        print("Testing lh negative")
        yield load_single(3<<2,0,LoadFunct3.RV32_F3_LH) ## Should read and sign extend the ff00 hword 
        _check(ls.result_o,0xffff8000,"lh negative test" )

        print("Testing lh positive")
        yield load_single(3<<2,2,LoadFunct3.RV32_F3_LH) ## Should read and sign extend the 0055 hword 
        _check(ls.result_o,0x705a,"lh positive test" )


    def run_all():
       yield sw_test()
       yield wait_valid()
      
       yield lw_test()
       yield wait_valid()
       yield sb_test()   
       yield wait_valid() 
       yield sh_test()
       yield wait_valid()
       yield load_other_test()


    def clear_ram():
        for m in ram:
           m.next = 0
        yield clock.posedge


        
    
    @instance
    def stimulus():
       global ram_latency

       ram_latency=1 
       yield run_all()
       yield clear_ram()
       print("Run with RAM wait state")
       ram_latency=2
       yield run_all()
       raise StopSimulation
         

    return instances()

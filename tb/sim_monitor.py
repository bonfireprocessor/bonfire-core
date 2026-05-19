"""
Bonfire Core simulation monitor
(c) 2019,2020 The Bonfire Project
License: See LICENSE
"""
from __future__ import print_function

from __future__ import print_function

from myhdl import *
from elftools.elf.elffile import ELFFile

from sys import stdout

def dump_signature(memArray,elf,sig):

    with open(elf,mode="rb") as f:
        elf = ELFFile(f)
        symtab = elf.get_section_by_name('.symtab')
        if symtab is None:
            # No symbols => cannot dump signature
            return

        start_sym = symtab.get_symbol_by_name("begin_signature")
        end_sym = symtab.get_symbol_by_name("end_signature")

        # Not all test programs provide signature symbols (e.g., simple hand-written tests).
        # In that case, skip dumping the signature instead of failing the whole run.
        if not start_sym or not end_sym:
            return

        start = start_sym[0]['st_value']
        end = end_sym[0]['st_value']
        assert(end > start)
        assert(end - start < 1000)

        sf=open(sig,"w")

        cnt=1
        for i in range(start>>2,end>>2):
            assert(i<len(memArray))
            h="{0:08x}".format(int(memArray[i]))
            stdout.write(h+ ("\n" if (cnt % 8)==0 else " "))
            cnt+=1
            sf.write(h+"\n")
        stdout.write("\n")    
        sf.close()

@block
def monitor_instance(memArray,bus,clock,base_adr=0x10000000,registered_ack=False,elfFile="",sigFile=""):

    @always(clock.posedge)
    def monitor_proc():

        if registered_ack and bus.ack_i:
            bus.ack_i.next = False 

        if bus.en_o:
            if bus.we_o:   
                print("Monitor write: @{} {}: {} ({})".format(now(),bus.adr_o,bus.db_wr,int(bus.db_wr.signed())))
                if bus.adr_o==base_adr:
                    if elfFile and sigFile:
                        dump_signature(memArray,elfFile,sigFile)
                    raise StopSimulation
            if registered_ack:    
                bus.ack_i.next = True         
    
    
    if not registered_ack:
        @always_comb
        def ack():
            bus.ack_i.next = bus.en_o

    return instances()

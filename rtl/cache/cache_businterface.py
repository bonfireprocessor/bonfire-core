"""
Bonfire Core Cache
(c) 2019,2020 The Bonfire Project
License: See LICENSE
"""

from myhdl import Signal,intbv,modbv, concat,  \
                  block,always_comb,always_seq, always, instances, enum, now

class BusInputBundle():
    def __init__(self,config,xlen=32):
        self.slave_en = Signal(bool(0))
        self.slave_adr_slice = Signal(modbv(0)[config.address_bits:]) # Slave adress slice stripped from lower (not used...) bits
        self.slave_we = Signal(modbv(0)[xlen//8:])
        self.slave_write = Signal(modbv(0)[xlen:])

class BusOutputBundle():
    def __init__(self,config,xlen=32):        
        self.slave_read =  Signal(modbv(0)[xlen:])
      

@block
def cache_dbslave_connect(db_slave,bus_input,bus_output,hit,clock,reset,config):

     # Constants
    slave_adr_low = db_slave.adrLow  
    slave_adr_high = slave_adr_low + config.address_bits

    slave_adr_reg =  Signal(modbv(0)[config.address_bits:])
    en_r = Signal(bool(0)) # Registered slave en signal
    slave_we_r = Signal(modbv(0)[len(db_slave.we_o):])
    slave_write_r = Signal(modbv(0)[db_slave.xlen:])
    slave_ack = Signal(bool(0))

    @always_comb
    def proc_input_comb():

        bus_input.slave_en.next = en_r or db_slave.en_o
        db_slave.stall_i.next = en_r and db_slave.en_o

        if en_r:
            bus_input.slave_adr_slice.next = slave_adr_reg
            bus_input.slave_we.next = slave_we_r
            bus_input.slave_write.next = slave_write_r
        else:
            bus_input.slave_adr_slice.next = db_slave.adr_o[slave_adr_high:slave_adr_low]
            bus_input.slave_we.next = db_slave.we_o
            bus_input.slave_write.next = db_slave.db_wr

    @always_comb
    def proc_output_comb():

        db_slave.ack_i.next = slave_ack
        db_slave.db_rd = bus_output.slave_read


    # Registers that do not need to be reset
    @always(clock.posedge)
    def proc_reg_slave():
        if db_slave.en_o and not ( en_r or hit ):
            slave_adr_reg.next = db_slave.adr_o[slave_adr_high:slave_adr_low]
            slave_we_r.next = db_slave.we_o
            slave_write_r.next = db_slave.db_wr        

    @always_seq(clock.posedge,reset)
    def proc_slave_control():

        if db_slave.en_o and not ( en_r or hit ):            
            en_r.next = True
            

        if hit and  ( db_slave.en_o or  en_r ):
            slave_ack.next = True
            en_r.next = False
        else:
           slave_ack.next = False

    return instances()

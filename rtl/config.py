class BonfireConfig:
    def __init__(self):
        self.shifter_mode="pipelined"
        self.xlen=32
        self.RVC = False # Support for Compressed ISA, not implemented yet
        self.jump_predictor = False # not used yet
        self.jump_bypass = True # bypass register stage for jump destination and branch result, reduces latency by 1 cylce
        self.mem_write_early_term = False # combinatorical mem write cylce termination on ack signal, creates comb. path between dbus ack and execute.valid_o 
        self.loadstore_outstanding = 1
        self.registered_read_stage = True #  register stage in loadstore unit between data bus and LSU output 
        self.reset_address=0x0
        self.max_mcause = 64 # Highest allows mcause value
        #ip_low contains lowest bit of valid instruction pointer
        if self.RVC:
            self.ip_low=1
        else:
            self.ip_low=2    

        
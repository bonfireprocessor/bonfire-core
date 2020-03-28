class BonfireConfig:
    def __init__(self):
        self.shifter_mode="pipelined"
        self.xlen=32
        self.jump_predictor = False
        self.jump_bypass = False # bypass register stage for jump destination and branch result, reduces latency by 1 cylce
        self.mem_write_early_term = False # combinatorical mem write cylce termination on ack signal, creates comb. path between dbus ack and execute.valid_o 
        self.loadstore_outstanding = 1
        self.registered_read_stage = True #  register stage in loadstore unit between data bus and LSU output 
        self.reset_address=0x0

        
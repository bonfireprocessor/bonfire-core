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
        self.mcause_max = 64 # Highest mcause reason
        self.enableDebugModule=False # Enable RISC-V Debug Module
        self.enableDebugNdmreset=False # Enable Debug Module non-debug-module reset control
        self.num_dscratch = 1 # Number of dscratch registers
        self.numdata = 1 # Number of Debug Data Registers
        self.dm_maxregno=0x101f
        self.dmi_adr_width=6 # DMI address width, 6 bits allows for 64 debug registers, which is more than the 0x101f max regno
        self.progbuf_size=2 # Currently the core only supports 1 and 2 for progbuf
        #ip_low contains lowest bit of valid instruction pointer
        if self.RVC:
            self.ip_low=1
        else:
            self.ip_low=2    

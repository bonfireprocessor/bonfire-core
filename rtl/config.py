class BonfireConfig:
    def __init__(self):
        self.shifter_mode="pipelined"
        self.xlen=32
        self.jump_predictor = False
        self.jump_bypass = False # bypassregister stage for jump destination and branch result, reduces latency by 1 cylce
        self.loadstore_outstanding = 1
        self.registered_read_stage = True #  register stage in loadstore unit between data bus and LSU output 
        self.reset_address=0x0

        
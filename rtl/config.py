class BonfireConfig:
    def __init__(self):
        self.shifter_mode="pipelined"
        self.xlen=32
        self.jump_predictor = False
        self.loadstore_outstanding = 1
        self.registered_read_stage = True #  register stage in loadstore unit between data bus and LSU output 

        
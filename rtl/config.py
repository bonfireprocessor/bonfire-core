class BonfireConfig:
    def __init__(self):
        self.shifter_mode="pipelined"
        self.xlen=32
        self.jump_predictor = False
        self.loadstore_outstanding = 1
        self.loadstore_combi = False # no register stage in loadstore output 

        
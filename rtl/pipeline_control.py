"""
Pipeline control class
(c) 2019,2020 The Bonfire Project
License: See LICENSE
"""

from __future__ import print_function

from myhdl import *

class PipelineControl:
    def __init__(self):
        self.en_i = Signal(bool(0)) # Input enable / valid
        self.busy_o = Signal(bool(0)) # unit busy (stall previous stage)

        self.valid_o = Signal(bool(0)) # Output valid
        self.stall_i = Signal(bool(0)) # Next stage stalled

        self.taken = Signal(bool(0)) # New operation taken
       
    @block
    def connect(self, clock,reset, **kwargs):

        if 'previous' in kwargs:
            prev_stage = kwargs['previous']
            @always_comb
            def connect_prev():
                self.en_i.next = prev_stage.valid_o
                prev_stage.stall_i.next = self.busy_o
                
        return instances()        

    @block   
    def pipeline_instance(self,busy,valid): 
        @always_comb
        def comb():
            self.taken.next = self.en_i and not busy
            self.busy_o.next = busy
            self.valid_o.next = valid  


        return instances()

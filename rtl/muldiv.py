"""
RV32M Multiply/Divide Issue, Completion, and Cancellation Control
(c) 2026 The Bonfire Project
License: See LICENSE

RV32M multiply/divide issue, completion, and cancellation control.
"""

from myhdl import Signal, always_comb, always_seq, block, instances, modbv

from rtl.divider import DividerBundle
from rtl.multiplier import MultiplierBundle


class MulDivBundle:
    """Pipeline request and completion contract for RV32M operations."""

    def __init__(self, config) -> None:
        self.op1_i = Signal(modbv(0)[config.xlen:])
        self.op2_i = Signal(modbv(0)[config.xlen:])
        self.operation_i = Signal(modbv(0)[3:])
        self.request_i = Signal(bool(0))
        self.cancel_i = Signal(bool(0))

        self.busy_o = Signal(bool(0))
        self.valid_o = Signal(bool(0))
        self.result_o = Signal(modbv(0)[config.xlen:])


class MulDivControllerBundle:
    """Pipeline-facing controller around the RV32M arithmetic units.

    ``port.request_i`` remains asserted while Decode is held. The controller
    converts it into a single request pulse, stalls Decode until completion,
    and suppresses a second request during the release cycle.
    """

    def __init__(self, config):
        self.config = config
        self.port = MulDivBundle(config)

        self.rd_i = Signal(modbv(0)[5:])
        self.rd_o = Signal(modbv(0)[5:])
        self.hazard_i = Signal(bool(0))
        self.consume_i = Signal(bool(0))

    @block
    def controller(self, clock, reset):
        pending = Signal(bool(0))
        start = Signal(bool(0))
        complete = Signal(bool(0))
        release = Signal(bool(0))

        if self.config.enable_m_extension:
            multiplier = MultiplierBundle(self.config.xlen)
            divider = DividerBundle(self.config.xlen)
            multiplier_inst = multiplier.multiplier(clock, reset)
            divider_inst = divider.divider(clock, reset)

            @always_comb
            def unit_connect():
                operation = self.port.operation_i
                is_division = bool(operation[2])

                start.next = self.port.request_i and \
                    not pending and not release and not self.hazard_i
                complete.next = multiplier.ce_o or divider.ce_o
                self.port.busy_o.next = pending or \
                    (self.port.request_i and not release)
                self.port.valid_o.next = complete

                if divider.ce_o:
                    self.port.result_o.next = divider.result_o
                else:
                    self.port.result_o.next = multiplier.result_o

                multiplier.op1_i.next = self.port.op1_i
                multiplier.op2_i.next = self.port.op2_i
                multiplier.ce_i.next = start and not is_division
                multiplier.cancel_i.next = self.port.cancel_i
                multiplier.high_i.next = operation != 0
                multiplier.signed_a_i.next = \
                    operation == 1 or operation == 2
                multiplier.signed_b_i.next = operation == 1

                divider.op1_i.next = self.port.op1_i
                divider.op2_i.next = self.port.op2_i
                divider.ce_i.next = start and is_division
                divider.cancel_i.next = self.port.cancel_i
                divider.signed_i.next = operation == 4 or operation == 6
                divider.rem_i.next = operation == 6 or operation == 7

            @always_seq(clock.posedge, reset=reset)
            def state():
                if self.port.cancel_i:
                    pending.next = False
                    release.next = False
                elif start:
                    pending.next = True
                    release.next = False
                    self.rd_o.next = self.rd_i
                elif complete:
                    pending.next = False
                    release.next = True
                elif release and self.consume_i:
                    release.next = False
        else:
            @always_comb
            def disabled():
                # Retain real sensitivity inputs for MyHDL conversion while
                # elaborating the disabled controller to constants.
                start.next = self.port.request_i and False
                complete.next = self.port.request_i and False
                self.port.busy_o.next = self.port.request_i and False
                self.port.valid_o.next = self.port.request_i and False
                if self.port.request_i:
                    self.port.result_o.next = self.port.op1_i
                else:
                    self.port.result_o.next = 0

        return instances()

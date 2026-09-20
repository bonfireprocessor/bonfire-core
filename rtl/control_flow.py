"""
Dynamic RV32I Branch and Jump Decision Logic
(c) 2026 The Bonfire Project
License: See LICENSE

Dynamic RV32I branch and jump decision logic.
"""

from myhdl import Signal, always_comb, block, modbv

from rtl.instructions import BranchFunct3 as b3


class ControlFlowBundle:
    """Branch/JAL/JALR decision and instruction-address validation outputs."""

    def __init__(self, config):
        xlen = config.xlen
        self.config = config
        self.branch_taken_o = Signal(bool(0))
        self.redirect_o = Signal(bool(0))
        self.link_write_o = Signal(bool(0))
        self.misaligned_o = Signal(bool(0))
        self.target_o = Signal(modbv(0)[xlen:])
        self.tval_o = Signal(modbv(0)[xlen:])

    @block
    def controller(
        self, branch_i, jump_i, jumpr_i, funct3_i, branch_target_i,
        jumpr_target_i, equal_i, ge_i, uge_i,
    ):
        xlen = self.config.xlen
        lower = self.config.ip_low

        @always_comb
        def decide():
            branch_taken = False
            redirect = False
            link_write = False
            misaligned = False
            target = modbv(0)[xlen:]

            if branch_i:
                if funct3_i == b3.RV32_F3_BEQ:
                    branch_taken = bool(equal_i)
                elif funct3_i == b3.RV32_F3_BNE:
                    branch_taken = not bool(equal_i)
                elif funct3_i == b3.RV32_F3_BLT:
                    branch_taken = not bool(ge_i)
                elif funct3_i == b3.RV32_F3_BGE:
                    branch_taken = bool(ge_i)
                elif funct3_i == b3.RV32_F3_BLTU:
                    branch_taken = not bool(uge_i)
                elif funct3_i == b3.RV32_F3_BGEU:
                    branch_taken = bool(uge_i)
                target[:] = branch_target_i
                misaligned = branch_taken and target[lower:0] != 0
                redirect = branch_taken and not misaligned
            elif jump_i:
                target[:] = branch_target_i
                misaligned = target[lower:0] != 0
                redirect = not misaligned
                link_write = not misaligned
            elif jumpr_i:
                target[:] = jumpr_target_i
                target[0] = False
                misaligned = target[lower:0] != 0
                redirect = not misaligned
                link_write = not misaligned

            self.branch_taken_o.next = branch_taken
            self.redirect_o.next = redirect
            self.link_write_o.next = link_write
            self.misaligned_o.next = misaligned
            self.target_o.next = target
            self.tval_o.next = target

        return decide

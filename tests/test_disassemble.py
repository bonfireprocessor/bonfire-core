from tb.disassemble import disassemble_rv32im
from rtl.instructions import Opcodes as op
from rtl.instructions import MulDivFunct as md
from rtl.instructions import BranchFunct3 as b3


def test_disassemble_add_and_fields():
    text, fields = disassemble_rv32im(0x00C586B3)

    assert text == "add a3,a1,a2"
    assert fields["opcode"] == op.RV32_OP
    assert fields["rd"] == 13
    assert fields["rs1"] == 11
    assert fields["rs2"] == 12


def test_disassemble_lbu_and_i_fields():
    text, fields = disassemble_rv32im(0x0054C303)

    assert text == "lbu t1,5(s1)"
    assert fields["opcode"] == op.RV32_LOAD
    assert fields["imm_i"] == 5
    assert fields["funct3"] == 4


def test_disassemble_mul_uses_m_extension():
    text, fields = disassemble_rv32im(0x02C58533)

    assert text == "mul a0,a1,a2"
    assert fields["opcode"] == op.RV32_OP
    assert fields["funct7"] == md.RV32_F7_MUL_DIV


def test_disassemble_branch_and_b_immediate():
    text, fields = disassemble_rv32im(0xFEC588E3)

    assert text == "beq a1,a2,-16"
    assert fields["opcode"] == op.RV32_BRANCH
    assert fields["funct3"] == b3.RV32_F3_BEQ
    assert fields["imm_b"] == -16


def test_disassemble_unknown_opcode_word_fallback():
    text, fields = disassemble_rv32im(0xFFFFFFFF)

    assert text == ".word 0xffffffff"
    assert fields["opcode_name"] == "UNKNOWN"

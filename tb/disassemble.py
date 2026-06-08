"""
RISC-V disassemble helper 
(c) 2019 The Bonfire Project
License: See LICENSE
"""

from rtl.instructions import Opcodes as op
from rtl.instructions import BranchFunct3 as b3
from rtl.instructions import LoadFunct3 as l3
from rtl.instructions import StoreFunct3 as s3
from rtl.instructions import ArithmeticFunct3 as a3
from rtl.instructions import FenceFunct3 as f3
from rtl.instructions import SystemFunct3 as y3
from rtl.instructions import PrivFunct12 as p12
from rtl.instructions import MulDivFunct as md

abi_regnames = ( "zero","ra","sp","gp","tp","t0","t1","t2","s0","s1","a0","a1","a2","a3","a4","a5", \
                 "a6","a7","s2","s3","s4","s5","s6","s7","s8","s9","s10","s11","t3","t4","t5","t6")


def abi_name(x):
    return abi_regnames[x]


def _sign_extend(value, width):
    sign = 1 << (width - 1)
    return (value & (sign - 1)) - (value & sign)


def _opcode_name(opcode):
    names = {
        op.RV32_LUI: "RV32_LUI",
        op.RV32_AUIPC: "RV32_AUIPC",
        op.RV32_JAL: "RV32_JAL",
        op.RV32_JALR: "RV32_JALR",
        op.RV32_BRANCH: "RV32_BRANCH",
        op.RV32_LOAD: "RV32_LOAD",
        op.RV32_STORE: "RV32_STORE",
        op.RV32_IMM: "RV32_IMM",
        op.RV32_OP: "RV32_OP",
        op.RV32_FENCE: "RV32_FENCE",
        op.RV32_SYSTEM: "RV32_SYSTEM",
    }
    return names.get(opcode, "UNKNOWN")


def decode_instruction_fields(word):
    """Decode raw RV32 instruction fields from a 32-bit instruction word."""
    word = int(word) & 0xFFFFFFFF

    opcode = (word >> 2) & 0x1F
    fields = {
        "word": word,
        "opcode7": word & 0x7F,
        "opcode": opcode,
        "opcode_name": _opcode_name(opcode),
        "rd": (word >> 7) & 0x1F,
        "funct3": (word >> 12) & 0x7,
        "rs1": (word >> 15) & 0x1F,
        "rs2": (word >> 20) & 0x1F,
        "funct7": (word >> 25) & 0x7F,
        "funct12": (word >> 20) & 0xFFF,
        "imm_i": _sign_extend((word >> 20) & 0xFFF, 12),
        "imm_s": _sign_extend((((word >> 25) & 0x7F) << 5) | ((word >> 7) & 0x1F), 12),
        "imm_b": _sign_extend(
            (((word >> 31) & 0x1) << 12)
            | (((word >> 7) & 0x1) << 11)
            | (((word >> 25) & 0x3F) << 5)
            | (((word >> 8) & 0xF) << 1),
            13,
        ),
        "imm_u": word & 0xFFFFF000,
        "imm_j": _sign_extend(
            (((word >> 31) & 0x1) << 20)
            | (((word >> 12) & 0xFF) << 12)
            | (((word >> 20) & 0x1) << 11)
            | (((word >> 21) & 0x3FF) << 1),
            21,
        ),
        "shamt": (word >> 20) & 0x1F,
    }
    return fields


def _disassemble_from_fields(fields):
    opcode = fields["opcode"]
    funct3 = fields["funct3"]
    funct7 = fields["funct7"]
    funct12 = fields["funct12"]
    rd = abi_name(fields["rd"])
    rs1 = abi_name(fields["rs1"])
    rs2 = abi_name(fields["rs2"])

    if opcode == op.RV32_LUI:
        return "lui {},0x{:x}".format(rd, fields["imm_u"] >> 12)
    if opcode == op.RV32_AUIPC:
        return "auipc {},0x{:x}".format(rd, fields["imm_u"] >> 12)
    if opcode == op.RV32_JAL:
        return "jal {},{}".format(rd, fields["imm_j"])
    if opcode == op.RV32_JALR:
        return "jalr {},{}({})".format(rd, fields["imm_i"], rs1)
    if opcode == op.RV32_BRANCH:
        names = {
            b3.RV32_F3_BEQ: "beq",
            b3.RV32_F3_BNE: "bne",
            b3.RV32_F3_BLT: "blt",
            b3.RV32_F3_BGE: "bge",
            b3.RV32_F3_BLTU: "bltu",
            b3.RV32_F3_BGEU: "bgeu",
        }
        m = names.get(funct3)
        if m is not None:
            return "{} {},{},{}".format(m, rs1, rs2, fields["imm_b"])
    if opcode == op.RV32_LOAD:
        names = {
            l3.RV32_F3_LB: "lb",
            l3.RV32_F3_LH: "lh",
            l3.RV32_F3_LW: "lw",
            l3.RV32_F3_LBU: "lbu",
            l3.RV32_F3_LHU: "lhu",
        }
        m = names.get(funct3)
        if m is not None:
            return "{} {},{}({})".format(m, rd, fields["imm_i"], rs1)
    if opcode == op.RV32_STORE:
        names = {
            s3.RV32_F3_SB: "sb",
            s3.RV32_F3_SH: "sh",
            s3.RV32_F3_SW: "sw",
        }
        m = names.get(funct3)
        if m is not None:
            return "{} {},{}({})".format(m, rs2, fields["imm_s"], rs1)
    if opcode == op.RV32_IMM:
        if funct3 == a3.RV32_F3_ADD_SUB:
            return "addi {},{},{}".format(rd, rs1, fields["imm_i"])
        if funct3 == a3.RV32_F3_SLT:
            return "slti {},{},{}".format(rd, rs1, fields["imm_i"])
        if funct3 == a3.RV32_F3_SLTU:
            return "sltiu {},{},{}".format(rd, rs1, fields["imm_i"])
        if funct3 == a3.RV32_F3_XOR:
            return "xori {},{},{}".format(rd, rs1, fields["imm_i"])
        if funct3 == a3.RV32_F3_OR:
            return "ori {},{},{}".format(rd, rs1, fields["imm_i"])
        if funct3 == a3.RV32_F3_AND:
            return "andi {},{},{}".format(rd, rs1, fields["imm_i"])
        if funct3 == a3.RV32_F3_SLL:
            return "slli {},{},{}".format(rd, rs1, fields["shamt"])
        if funct3 == a3.RV32_F3_SRL_SRA:
            if (funct7 >> 5) & 0x1:
                return "srai {},{},{}".format(rd, rs1, fields["shamt"])
            return "srli {},{},{}".format(rd, rs1, fields["shamt"])
    if opcode == op.RV32_OP:
        if funct7 == md.RV32_F7_MUL_DIV:
            names = {
                md.RV32_F3_MUL: "mul",
                md.RV32_F3_MULH: "mulh",
                md.RV32_F3_MULHSU: "mulhsu",
                md.RV32_F3_MULHU: "mulhu",
                md.RV32_F3_DIV: "div",
                md.RV32_F3_DIVU: "divu",
                md.RV32_F3_REM: "rem",
                md.RV32_F3_REMU: "remu",
            }
            m = names.get(funct3)
            if m is not None:
                return "{} {},{},{}".format(m, rd, rs1, rs2)
        if funct3 == a3.RV32_F3_ADD_SUB:
            if (funct7 >> 5) & 0x1:
                return "sub {},{},{}".format(rd, rs1, rs2)
            return "add {},{},{}".format(rd, rs1, rs2)
        if funct3 == a3.RV32_F3_SLL:
            return "sll {},{},{}".format(rd, rs1, rs2)
        if funct3 == a3.RV32_F3_SLT:
            return "slt {},{},{}".format(rd, rs1, rs2)
        if funct3 == a3.RV32_F3_SLTU:
            return "sltu {},{},{}".format(rd, rs1, rs2)
        if funct3 == a3.RV32_F3_XOR:
            return "xor {},{},{}".format(rd, rs1, rs2)
        if funct3 == a3.RV32_F3_SRL_SRA:
            if (funct7 >> 5) & 0x1:
                return "sra {},{},{}".format(rd, rs1, rs2)
            return "srl {},{},{}".format(rd, rs1, rs2)
        if funct3 == a3.RV32_F3_OR:
            return "or {},{},{}".format(rd, rs1, rs2)
        if funct3 == a3.RV32_F3_AND:
            return "and {},{},{}".format(rd, rs1, rs2)
    if opcode == op.RV32_FENCE:
        if funct3 == f3.RV32_F3_FENCE:
            return "fence"
        if funct3 == f3.RV32_F3_FENCE_I:
            return "fence.i"
    if opcode == op.RV32_SYSTEM:
        if funct3 == y3.RV32_F3_PRIV:
            if funct12 == p12.RV32_F12_ECALL:
                return "ecall"
            if funct12 == p12.RV32_F12_EBREAK:
                return "ebreak"
            if funct12 == p12.RV32_F12_ERET:
                return "eret"
        names = {
            y3.RV32_F3_CSRRW: "csrrw",
            y3.RV32_F3_CSRRS: "csrrs",
            y3.RV32_F3_CSRRC: "csrrc",
            y3.RV32_F3_CSRRWI: "csrrwi",
            y3.RV32_F3_CSRRSI: "csrrsi",
            y3.RV32_F3_CSRRCI: "csrrci",
        }
        m = names.get(funct3)
        if m is not None:
            src = fields["rs1"] if funct3 in (y3.RV32_F3_CSRRWI, y3.RV32_F3_CSRRSI, y3.RV32_F3_CSRRCI) else rs1
            return "{} {},0x{:03x},{}".format(m, rd, funct12, src)

    return ".word 0x{:08x}".format(fields["word"])


def disassemble_rv32im(word):
    """Disassemble a RV32IM instruction and return text plus decoded fields."""
    fields = decode_instruction_fields(word)
    return _disassemble_from_fields(fields), fields


def disassemble(word):
    return disassemble_rv32im(word)

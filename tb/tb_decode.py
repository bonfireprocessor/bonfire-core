from __future__ import print_function

from myhdl import *
from rtl.decode import *
from tb.ClkDriver import *


clock = Signal(bool(0))
reset = ResetSignal(0, active=1, isasync=False)

dec = DecodeBundle()


# The source fields are checked independently of their use classification:
# immediate fields still appear on source_rs*, but must not create hazards.
commands = [
    {"opcode": 0x00500593, "source": "li a1,5", "uses_rs1": True, "uses_rs2": False},
    {"opcode": 0x00c586b3, "source": "add a3,a1,a2", "uses_rs1": True, "uses_rs2": True},
    {"opcode": 0x02c586b3, "source": "mul a3,a1,a2", "uses_rs1": True, "uses_rs2": True},
    {"opcode": 0x00062683, "source": "lw a3,0(a2)", "uses_rs1": True, "uses_rs2": False},
    {"opcode": 0x00d62023, "source": "sw a3,0(a2)", "uses_rs1": True, "uses_rs2": True},
    {"opcode": 0xfec588e3, "source": "beq a1,a2,0", "current_ip": 16, "uses_rs1": True, "uses_rs2": True},
    {"opcode": 0x000000ef, "source": "jal ra,0", "uses_rs1": False, "uses_rs2": False},
    {"opcode": 0x000606e7, "source": "jalr a3,0(a2)", "uses_rs1": True, "uses_rs2": False},
    {"opcode": 0x000016b7, "source": "lui a3,1", "uses_rs1": False, "uses_rs2": False},
    {"opcode": 0x00001697, "source": "auipc a3,1", "uses_rs1": False, "uses_rs2": False},
    {"opcode": 0x300616f3, "source": "csrrw a3,mstatus,a2", "uses_rs1": True, "uses_rs2": False},
    {"opcode": 0x3001d6f3, "source": "csrrwi a3,mstatus,3", "uses_rs1": False, "uses_rs2": False},
    {"opcode": 0x0000000f, "source": "fence", "uses_rs1": False, "uses_rs2": False},
    {"opcode": 0x00000073, "source": "ecall", "uses_rs1": False, "uses_rs2": False},
    {"opcode": 0x00002063, "source": "reserved branch funct3", "uses_rs1": False, "uses_rs2": False},
]


@block
def tb(test_conversion=False):

    clk_driver = ClkDriver(clock)
    inst = DecodeBundle.decoder(dec, clock, reset)

    if test_conversion:
        inst.convert(hdl='VHDL', std_logic_ports=True, path='vhdl_gen', name="decode")

    def assert_decoded(cmd):
        opcode = cmd["opcode"]
        assert dec.valid_o, "{} was not accepted".format(cmd["source"])
        assert int(dec.source_rs1_o) == (opcode >> 15) & 0x1f
        assert int(dec.source_rs2_o) == (opcode >> 20) & 0x1f
        assert bool(dec.uses_rs1_o) == cmd["uses_rs1"]
        assert bool(dec.uses_rs2_o) == cmd["uses_rs2"]

    def issue(cmd):
        dec.word_i.next = cmd["opcode"]
        ip = cmd.get("current_ip", 0)
        dec.current_ip_i.next = ip
        dec.next_ip_i.next = ip + 4
        dec.en_i.next = True
        yield clock.posedge
        yield delay(1)
        assert_decoded(cmd)

    @instance
    def stimulus():
        for cmd in commands:
            yield issue(cmd)

        # While Execute stalls Decode, rs*_adr_o must address the held
        # instruction rather than the new look-ahead word.  The registered
        # source metadata and its use flags must remain unchanged as well.
        held = commands[1]
        yield issue(held)
        look_ahead = commands[3]
        dec.word_i.next = look_ahead["opcode"]
        dec.stall_i.next = True
        yield delay(1)
        assert dec.busy_o
        assert int(dec.rs1_adr_o) == (held["opcode"] >> 15) & 0x1f
        assert int(dec.rs2_adr_o) == (held["opcode"] >> 20) & 0x1f
        assert_decoded(held)
        yield clock.posedge
        yield delay(1)
        assert_decoded(held)

        dec.stall_i.next = False
        yield clock.posedge
        yield delay(1)
        assert_decoded(look_ahead)

        dec.en_i.next = False
        raise StopSimulation

    return instances()

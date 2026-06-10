from __future__ import annotations

from math import log

from myhdl import *

from gdbserver.main import ServerControl, tcp_server
from rtl import bonfire_core_top, bonfire_interfaces, config
from rtl.debugModule import AbstractDebugTransportBundle
from tb.ClkDriver import ClkDriver
from tb.disassemble import disassemble
from tb.sim_ram import sim_ram


class GDBServerTestbench:
    def __init__(
        self,
        config: config.BonfireConfig = config.BonfireConfig(),
        hexfile: str = "",
        ramsize: int = 16384,
        server_control: ServerControl | None = None,
    ) -> None:
        self.config = config
        self.hexfile = hexfile
        self.ramsize = ramsize
        self.server_control = server_control or ServerControl()
        if self.server_control.memory_size_bytes is None:
            self.server_control.memory_size_bytes = ramsize * 4

    def create_ram(self, progfile: str, ramsize: int):
        ram = []
        adr = 0

        with open(progfile, "r") as f:
            for line in f:
                i = int(line, 16)
                ram.append(Signal(intbv(i)[32:]))
                adr += 1

        print("eof at adr:{}".format(hex(adr << 2)))
        for _ in range(adr, ramsize):
            ram.append(Signal(intbv(0)[32:]))

        print("Created ram with size {} words".format(len(ram)))
        return ram

    @block
    def testbench(self):
        clock = Signal(bool(0))
        reset = ResetSignal(0, active=1, isasync=False)

        local_config = self.config
        local_config.enableDebugModule = True
        dtm = AbstractDebugTransportBundle(local_config)

        ram = self.create_ram(self.hexfile, self.ramsize)

        ibus = bonfire_interfaces.DbusBundle(local_config, readOnly=True)
        dbus = bonfire_interfaces.DbusBundle(local_config)
        control = bonfire_interfaces.ControlBundle(local_config)
        debug = bonfire_interfaces.DebugOutputBundle(local_config)

        ram_dbus = bonfire_interfaces.DbusBundle(local_config)
        ram_sel_r = Signal(bool(0))

        mem = sim_ram()
        mem.setLatency(1)

        ibus_if = mem.ram_interface(ram, ibus, clock, reset, readOnly=True)
        dbus_if = mem.ram_interface(ram, ram_dbus, clock, reset)

        clk_driver = ClkDriver(clock)
        server_i = tcp_server(dtm, clock, control=self.server_control)

        core = bonfire_core_top.BonfireCoreTop(local_config)
        dut = core.createInstance(ibus, dbus, control, clock, reset, debug, debugTransportBundle=dtm)

        @always_seq(clock.posedge, reset=reset)
        def slave_select():
            if ram_sel_r and ram_dbus.ack_i:
                ram_sel_r.next = False
            elif dbus.en_o and dbus.adr_o >> 2 < self.ramsize:
                ram_sel_r.next = True

        @always_comb
        def slave_connect():
            ram_sel = dbus.en_o and dbus.adr_o >> 2 < self.ramsize
            ram_dbus.en_o.next = ram_sel
            ram_dbus.we_o.next = dbus.we_o
            ram_dbus.adr_o.next = dbus.adr_o[log(self.ramsize, 2) + 2:]
            ram_dbus.db_wr.next = dbus.db_wr

            dbus.stall_i.next = ram_dbus.stall_i
            dbus.ack_i.next = ram_dbus.ack_i
            dbus.db_rd.next = ram_dbus.db_rd

        @always_seq(clock.posedge, reset=reset)
        def sim_observe():
            d = core.backend.decode
            inv = d.en_i and d.invalid_opcode and not d.kill_i
            if inv:
                instr = int(d.word_i)
                asm, _ = disassemble(instr)
                assert False, "Invalid opcode @{}: pc:0x{:08x} op:0x{:08x} {} ".format(now(), int(d.current_ip_i), instr, asm)

        return instances()

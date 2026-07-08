"""
Bonfire Core simulation GDB server runner
(c) 2019-2026 The Bonfire Project
LICENSE: GPLv3, see below.
This file is derived work from gdbserver.py:
"""

#
#    gdbserver.py - Control OllyDBG2 with GDB over the network! (for fun)
#    Copyright (C) 2013 Axel "0vercl0k" Souchet - http://www.twitter.com/0vercl0k
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import logging
import struct
from collections.abc import Generator
from io import BytesIO
from typing import Any, Callable

GDB_SIGNAL_TRAP = 5
EBREAK_INSN = 0x00100073


def checksum(data: str) -> int:
    checksum = 0
    for c in data:
        checksum += ord(c)
    return checksum & 0xFF


def _hex_encode_text(text: str) -> str:
    """Encode an ASCII string as hex bytes for qRcmd / console output."""
    return text.encode('ascii', errors='replace').hex().upper()


class RSPHandler(object):
    def __init__(self, clientsocket: Any, debugAPI: Any, readySignal: Any) -> None:
        self.clientsocket = clientsocket
        self.netin: BytesIO | None = None
        self.netout = clientsocket.makefile('w')
        self.debugAPI = debugAPI
        self.readySignal = readySignal
        self.breakpoints: dict[int, bytes] = {}

        logging.basicConfig(level=logging.WARN)
        for logger in 'rsphandler runner main'.split(' '):
            logging.getLogger(logger).setLevel(level=logging.INFO)

        self.log = logging.getLogger('rsphandler')
        self.last_pkt: str | None = None
        # Allow the simulation wrapper to expose a RAM size so out-of-range
        # memory reads/writes return an RSP error instead of hanging.
        self.memory_size_bytes: int | None = getattr(debugAPI, 'memory_size_bytes', None)

    def close(self) -> None:
        # Close netin only when it was created.
        if self.netin is not None:
            self.netin.close()
        self.netout.close()
        self.clientsocket.close()
        self.log.info('closed')

    # Guard simulated memory accesses so unsupported addresses fail with E01
    # instead of stalling the testbench forever.
    def _memory_range_valid(self, addr: int, size: int) -> bool:
        if addr < 0 or size < 0:
            return False
        if self.memory_size_bytes is None:
            return True
        return addr + size <= self.memory_size_bytes

    # Used by memory write handling and optional software-breakpoint patching.
    def _write_memory_bytes(self, addr: int, data: bytes) -> Generator[Any, None, None]:
        for offset, value in enumerate(data):
            yield self.debugAPI.writeMemory(memadr=addr + offset, memvalue=value, writeByte=True)

    # Manipulate dcsr bits needed by the single-step / breakpoint-related flows.
    def _update_dcsr(self, ebreakm: bool | None = None, step: bool | None = None) -> Generator[Any, None, None]:
        from rtl.instructions import CSRAdr

        dcsr = 0x700 | CSRAdr.dcsr
        yield self.debugAPI.readCSR(csr_adr=dcsr)
        value = self.debugAPI.cmd_result()
        if ebreakm is not None:
            if ebreakm:
                value |= (1 << 15)
            else:
                value &= ~(1 << 15)
        if step is not None:
            if step:
                value |= (1 << 2)
            else:
                value &= ~(1 << 2)
        yield self.debugAPI.writeCSR(csr_adr=dcsr, value=value)

    # Renamed from 'bytes' to 'packet_bytes' to avoid shadowing Python's
    # built-in bytes type.
    def run_cmd(self, packet_bytes: bytes) -> Generator[Any, None, None]:
        result = self.receive(packet_bytes)
        if result == 'Good':
            pkt = self.last_pkt
            assert pkt is not None
            self.log.debug('receive(%r)' % pkt)
            self.send_raw('+')

            def handle_q(subcmd: str) -> Generator[Any, None, None]:
                if subcmd.startswith('Supported'):
                    self.log.info('Received qSupported command')
                    self.send('PacketSize=%x;swbreak+' % 4096)
                elif subcmd.startswith('Attached'):
                    self.log.info('Received qAttached command')
                    self.log.info('Trying to halt core')
                    yield self.debugAPI.halt()
                    self.log.info('Core Halted')
                    self.send('0')
                elif subcmd.startswith('C'):
                    # Reply with a proper qC thread-id response.
                    self.send('QC0')
                elif subcmd.startswith('Rcmd,'):
                    hex_cmd = subcmd[5:]
                    try:
                        cmd_text = bytes.fromhex(hex_cmd).decode('ascii', errors='replace').strip().lower()
                    except ValueError:
                        self.send('E01')
                        return
                    self.log.info('monitor command: %r' % cmd_text)
                    if cmd_text == 'halt':
                        yield self.debugAPI.halt()
                        self.send('OK')
                    elif cmd_text == 'resume':
                        yield self.debugAPI.resume()
                        self.send(_hex_encode_text('Core resumed\n'))
                    elif cmd_text == 'reset':
                        yield self.debugAPI.ResetCore()
                        yield self.debugAPI.halt()
                        self.send('OK')
                    else:
                        self.send(_hex_encode_text('Unknown monitor command: %s\n' % cmd_text))
                else:
                    self.log.error('This subcommand %r is not implemented in q' % subcmd)
                    self.send('')

            def handle_h(subcmd: str) -> None:
                self.send('OK')

            def handle_qmark(subcmd: str) -> None:
                self.send('S%.2x' % GDB_SIGNAL_TRAP)

            def handle_g(subcmd: str) -> Generator[Any, None, None]:
                from rtl.instructions import CSRAdr

                if subcmd == '':
                    self.log.info('Register Read subcommand')
                    registers = [0 for _ in range(33)]
                    registers[0] = 0
                    for i in range(1, 32):
                        yield self.debugAPI.readGPR(regno=i)
                        registers[i] = self.debugAPI.cmd_result()

                    yield self.debugAPI.readCSR(csr_adr=0x700 | CSRAdr.dpc)
                    registers[32] = self.debugAPI.cmd_result()

                    s = ''
                    for r in registers:
                        p = struct.pack('<I', r)
                        for b in p:
                            s += ("{:02X}".format(b))
                    self.send(s)

            def handle_m(subcmd: str) -> Generator[Any, None, None]:
                addr, size = subcmd.split(',')
                addr = int(addr, 16)
                size = int(size, 16)
                self.log.info('Received a "read memory" command (@%#.8x : %d bytes)' % (addr, size))
                if not self._memory_range_valid(addr, size):
                    self.send("E01")
                    return
                s = ""
                for i in range(addr, addr + size):
                    yield self.debugAPI.readMemory(memadr=i, readbyte=True)
                    s += ("{:02X}".format(self.debugAPI.cmd_result()))
                self.send(s)

            def handle_M(subcmd: str) -> Generator[Any, None, None]:
                addr, tail = subcmd.split(',')
                size, hexstring = tail.split(':')
                addr = int(addr, 16)
                size = int(size, 16)
                if not self._memory_range_valid(addr, size):
                    self.send("E01")
                elif size * 2 != len(hexstring):
                    self.log.error('Memory Write Command, size mismatch')
                    self.send("E01")
                else:
                    yield self._write_memory_bytes(addr, bytes.fromhex(hexstring))
                    self.send("OK")

            def handle_P(subcmd: str) -> Generator[Any, None, None]:
                from rtl.instructions import CSRAdr

                regnum, value = subcmd.split('=')
                regnum = int(regnum, 16)
                value = int(value, 16)
                if regnum in range(0, 32):
                    regnum += 0x1000
                    yield self.debugAPI.writeReg(regno=regnum, value=value)
                elif regnum == 32:
                    yield self.debugAPI.writeCSR(csr_adr=(0x700 | CSRAdr.dpc), value=value)
                else:
                    self.log.error('invalid register number %d in P command' % (regnum))
                    self.send("E01")
                    return

                self.send("OK")

            def handle_s(subcmd: str) -> Generator[Any, None, None]:
                self.log.info('Received a "single step" command')
                # Try to map GDB single-step onto dcsr.step.
                yield self._update_dcsr(ebreakm=bool(self.breakpoints), step=True)
                yield self.debugAPI.resume()
                while True:
                    yield self.debugAPI.yield_clock()
                    yield self.debugAPI.check_halted()
                    if self.debugAPI.halted:
                        yield self._update_dcsr(step=False)
                        self.send('T%.2x' % GDB_SIGNAL_TRAP)
                        return

            def handle_c(subcmd: str) -> Generator[Any, None, None]:
                from rtl.instructions import CSRAdr

                self.log.info("Received continue command")
                if subcmd:
                    addr = int(subcmd, 16)
                    self.log.info(' continue at (@%#.8x )' % (addr))
                    yield self.debugAPI.writeCSR(csr_adr=(0x700 | CSRAdr.dpc), value=addr)

                if self.breakpoints:
                    # If software breakpoints were patched into memory,
                    # enable dcsr.ebreakm before resuming.
                    yield self._update_dcsr(ebreakm=True)

                yield self.debugAPI.resume()
                self.log.info('Core resumed')

                if self.breakpoints:
                    while True:
                        yield self.debugAPI.yield_clock()
                        yield self.debugAPI.check_halted()
                        if self.debugAPI.halted:
                            self.send('T%.2x' % GDB_SIGNAL_TRAP)
                            return

            def handle_G(subcmd: str) -> Generator[Any, None, None]:
                from rtl.instructions import CSRAdr

                self.log.info('Write all registers command')
                # subcmd is 33 * 8 hex chars = 264 chars (32 GPRs + PC)
                if len(subcmd) < 33 * 8:
                    self.send('E01')
                    return
                try:
                    values = []
                    for i in range(33):
                        raw = bytes.fromhex(subcmd[i * 8:(i + 1) * 8])
                        values.append(int.from_bytes(raw, byteorder='little'))
                except ValueError:
                    self.log.error('G command: invalid hex data')
                    self.send('E01')
                    return
                # x0 is always 0; skip writing it (write x1..x31)
                for i in range(1, 32):
                    yield self.debugAPI.writeReg(regno=i + 0x1000, value=values[i])
                yield self.debugAPI.writeCSR(csr_adr=(0x700 | CSRAdr.dpc), value=values[32])
                self.send('OK')

            def handle_X(subcmd: str) -> Generator[Any, None, None]:
                colon = subcmd.find(':')
                if colon == -1:
                    self.send('E01')
                    return
                addr_size = subcmd[:colon]
                binary_data = subcmd[colon + 1:]
                addr, size = addr_size.split(',')
                addr = int(addr, 16)
                size = int(size, 16)
                if size == 0:
                    # GDB probes support with a zero-length write; just acknowledge.
                    self.send('OK')
                    return
                if not self._memory_range_valid(addr, size):
                    self.send('E01')
                    return
                # binary_data was decoded with latin-1 so each char maps to one byte.
                data_bytes = binary_data[:size].encode('latin-1')
                if len(data_bytes) != size:
                    self.send('E01')
                    return
                yield self._write_memory_bytes(addr, data_bytes)
                self.send('OK')

            def handle_Z(subcmd: str) -> Generator[Any, None, None]:
                try:
                    kind, addr, size = subcmd.split(',')
                    addr = int(addr, 16)
                    size = int(size, 16)
                except ValueError:
                    self.log.error('Z command: malformed packet %r' % subcmd)
                    self.send('E01')
                    return
                if kind != '0':
                    self.send('')
                    return
                if not self._memory_range_valid(addr, size):
                    self.send("E01")
                    return
                if addr not in self.breakpoints:
                    original = bytearray()
                    for i in range(addr, addr + size):
                        yield self.debugAPI.readMemory(memadr=i, readbyte=True)
                        original.append(self.debugAPI.cmd_result() & 0xFF)
                    self.breakpoints[addr] = bytes(original)
                    yield self._write_memory_bytes(addr, EBREAK_INSN.to_bytes(4, byteorder='little')[:size])
                self.send('OK')

            def handle_z(subcmd: str) -> Generator[Any, None, None]:
                try:
                    kind, addr, size = subcmd.split(',')
                    addr = int(addr, 16)
                    size = int(size, 16)
                except ValueError:
                    self.log.error('z command: malformed packet %r' % subcmd)
                    self.send('E01')
                    return
                if kind != '0':
                    self.send('')
                    return
                if not self._memory_range_valid(addr, size):
                    self.send("E01")
                    return
                original = self.breakpoints.pop(addr, None)
                if original is not None:
                    yield self._write_memory_bytes(addr, original)
                if not self.breakpoints:
                    yield self._update_dcsr(ebreakm=False)
                self.send('OK')

            def handle_D(subcmd: str) -> None:
                # Acknowledge detach explicitly.
                self.send('OK')

            def handle_v(subcmd: str) -> Generator[Any, None, None]:
                if subcmd == 'Cont?':
                    # Report supported vCont actions: continue, step.
                    self.send('vCont;c;s')
                elif subcmd.startswith('Cont;'):
                    actions = subcmd[5:].split(';')
                    # Use the first action that applies to all threads or thread 1.
                    action = actions[0].split(':')[0] if actions else ''
                    if action == 'c':
                        yield handle_c('')
                    elif action == 's':
                        yield handle_s('')
                    else:
                        self.log.info('vCont action %r not handled' % action)
                        self.send('')
                else:
                    # Answer unknown v-packets with an empty response.
                    self.send('')

            dispatchers: dict[str, Callable[[str], object]] = {
                'q': handle_q,
                'H': handle_h,
                '?': handle_qmark,
                'g': handle_g,
                'G': handle_G,
                'm': handle_m,
                's': handle_s,
                'c': handle_c,
                'M': handle_M,
                'X': handle_X,
                'P': handle_P,
                'Z': handle_Z,
                'z': handle_z,
                'D': handle_D,
                'v': handle_v,
            }

            cmd, subcmd = pkt[0], pkt[1:]
            if cmd == 'k':
                pass

            if cmd not in dispatchers:
                self.log.info('%r command not handled' % pkt)
                self.send('')
            else:
                yield dispatchers[cmd](subcmd)
        elif result == "Break":
            self.log.info("Break received, halting core")
            yield self.debugAPI.halt()
            self.log.info("Core halted")
            self.send('T%.2x' % GDB_SIGNAL_TRAP)

        self.readySignal.next = True

    # Renamed from 'bytes' to 'packet_bytes' to avoid shadowing Python's
    # built-in bytes type.
    def receive(self, packet_bytes: bytes) -> str:
        csum = 0
        state = 'Finding SOP'
        packet = ''
        self.netin = BytesIO(packet_bytes)
        escaped = False
        while True:
            c = self.netin.read(1)
            if c == b'\x03':
                return 'Break'

            if len(c) != 1:
                return 'Error: EOF'

            if state == 'Finding SOP':
                if c == b'$':
                    state = 'Finding EOP'
            elif state == 'Finding EOP':
                # Per RSP spec, the checksum covers all raw (escaped) bytes
                # between '$' and '#', including the '}' escape prefix byte
                # and the XOR'd byte that follows it.
                csum = (csum + ord(c)) & 0xFF
                if escaped:
                    # Unescape: XOR with 0x20.
                    packet += chr(ord(c) ^ 0x20)
                    escaped = False
                elif c == b'}':
                    # RSP escape prefix; next byte will be XOR'd with 0x20.
                    escaped = True
                elif c == b'#':
                    # End-of-packet marker: remove the '#' contribution from
                    # the checksum (it was added above before we detected it).
                    csum = (csum - ord(c)) & 0xFF
                    if csum != int(self.netin.read(2), 16):
                        raise Exception('invalid checksum')
                    self.last_pkt = packet
                    return 'Good'
                else:
                    # Use latin-1 so that all byte values 0x00–0xFF survive
                    # the decode round-trip (needed for binary X packets).
                    packet += c.decode('latin-1')
            else:
                raise Exception('should not be here')

    def send(self, msg: str) -> None:
        self.log.debug('send(%r)' % msg)
        self.send_raw('$%s#%.2x' % (msg, checksum(msg)))

    def send_raw(self, r: str) -> None:
        self.netout.write(r)
        self.netout.flush()

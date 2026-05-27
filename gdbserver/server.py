#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import struct

GDB_SIGNAL_TRAP = 5


def checksum(data):
    checksum = 0
    for c in data:
        checksum += ord(c)
    return checksum & 0xFF


class GDBClientHandler(object):
    def __init__(self, clientsocket, debugAPI, readySignal):
        self.clientsocket = clientsocket
        self.netin = None
        self.netout = clientsocket.makefile('w')
        self.debugAPI = debugAPI
        self.readySignal = readySignal

        logging.basicConfig(level=logging.WARN)
        for logger in 'gdbclienthandler runner main'.split(' '):
            logging.getLogger(logger).setLevel(level=logging.INFO)

        self.log = logging.getLogger('gdbclienthandler')
        self.last_pkt = None

    def close(self):
        self.netin.close()
        self.netout.close()
        self.clientsocket.close()
        self.log.info('closed')

    def run_cmd(self, bytes):
        result = self.receive(bytes)
        if result == 'Good':
            pkt = self.last_pkt
            self.log.debug('receive(%r)' % pkt)
            self.send_raw('+')

            def handle_q(subcmd):
                if subcmd.startswith('Supported'):
                    self.log.info('Received qSupported command')
                    self.send('PacketSize=%x' % 4096)
                elif subcmd.startswith('Attached'):
                    self.log.info('Received qAttached command')
                    self.log.info('Trying to halt core')
                    yield self.debugAPI.halt()
                    self.log.info('Core Halted')
                    self.send('0')
                elif subcmd.startswith('C'):
                    self.send('T%.2x;0')
                else:
                    self.log.error('This subcommand %r is not implemented in q' % subcmd)
                    self.send('')

            def handle_h(subcmd):
                self.send('OK')

            def handle_qmark(subcmd):
                self.send('S%.2x' % GDB_SIGNAL_TRAP)

            def handle_g(subcmd):
                from rtl.instructions import CSRAdr

                if subcmd == '':
                    self.log.info('Register Read subcommand')
                    registers = [0 for _ in range(33)]
                    registers[0] = 0
                    for i in range(1, 32):
                        yield self.debugAPI.readGPR(regno=i)
                        registers[i] = self.debugAPI.cmd_result()

                    yield self.debugAPI.readReg(regno=0x700 | CSRAdr.dpc)
                    registers[32] = self.debugAPI.cmd_result()

                    s = ''
                    for r in registers:
                        p = struct.pack('<I', r)
                        for b in p:
                            s += ("{:02X}".format(b))
                    self.send(s)

            def handle_m(subcmd):
                addr, size = subcmd.split(',')
                addr = int(addr, 16)
                size = int(size, 16)
                self.log.info('Received a "read memory" command (@%#.8x : %d bytes)' % (addr, size))
                s = ""
                for i in range(addr, addr + size):
                    yield self.debugAPI.readMemory(memadr=i, readbyte=True)
                    s += ("{:02X}".format(self.debugAPI.cmd_result()))

                self.send(s)

            def handle_M(subcmd):
                addr, tail = subcmd.split(',')
                size, hexstring = tail.split(':')
                addr = int(addr, 16)
                size = int(size, 16)
                if size * 2 != len(hexstring):
                    self.log.error('Memory Write Command, size mismatch')
                    self.send("E01")
                else:
                    for i in range(0, len(hexstring), 2):
                        byte_value = int(hexstring[i:i + 2], 16)
                        yield self.debugAPI.writeMemory(memadr=addr, memvalue=byte_value, writeByte=True)
                        addr += 1
                self.send("OK")

            def handle_P(subcmd):
                from rtl.instructions import CSRAdr

                regnum, value = subcmd.split('=')
                regnum = int(regnum, 16)
                value = int(value, 16)
                if regnum in range(0, 32):
                    regnum += 0x1000
                elif regnum == 32:
                    regnum = (0x700 | CSRAdr.dpc)
                else:
                    self.log.error('invalid register number %d in P command' % (regnum))
                    self.send("E01")
                    return

                yield self.debugAPI.writeReg(regno=regnum, value=value)
                self.send("OK")

            def handle_s(subcmd):
                self.log.info('Received a "single step" command')
                self.send('T%.2x' % GDB_SIGNAL_TRAP)

            def handle_c(subcmd):
                from rtl.instructions import CSRAdr

                self.log.info("Received continue command")
                if subcmd:
                    addr = int(subcmd, 16)
                    self.log.info(' continue at (@%#.8x )' % (addr))
                    yield self.debugAPI.writeReg(regno=(0x700 | CSRAdr.dpc), value=addr)
                yield self.debugAPI.resume()
                self.log.info('Core resumed')

            dispatchers = {
                'q': handle_q,
                'H': handle_h,
                '?': handle_qmark,
                'g': handle_g,
                'm': handle_m,
                's': handle_s,
                'c': handle_c,
                'M': handle_M,
                'P': handle_P,
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

    def receive(self, bytes):
        from io import BytesIO

        csum = 0
        state = 'Finding SOP'
        packet = ''
        self.netin = BytesIO(bytes)
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
                if c == b'#':
                    if csum != int(self.netin.read(2), 16):
                        raise Exception('invalid checksum')
                    self.last_pkt = packet
                    return 'Good'
                else:
                    packet += c.decode(encoding="ASCII", errors="ignore")
                    csum = (csum + ord(c)) & 0xFF
            else:
                raise Exception('should not be here')

    def send(self, msg):
        self.log.debug('send(%r)' % msg)
        self.send_raw('$%s#%.2x' % (msg, checksum(msg)))

    def send_raw(self, r):
        self.netout.write(r)
        self.netout.flush()

#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
#from ollyapi import *
import sys
import socket
import logging
import struct

GDB_SIGNAL_TRAP = 5

def checksum(data):
    checksum = 0
    for c in data:
        checksum += ord(c)
    return checksum & 0xff

# Code a bit inspired from http://mspgcc.cvs.sourceforge.net/viewvc/mspgcc/msp430simu/gdbserver.py?revision=1.3&content-type=text%2Fplain
class GDBClientHandler(object):
    def __init__(self, clientsocket):
        self.clientsocket = clientsocket
        self.netin = None
        self.netout = clientsocket.makefile('w')
        self.log = logging.getLogger('gdbclienthandler')
        self.last_pkt = None

    def close(self):
        '''End of story!'''
        self.netin.close()
        self.netout.close()
        self.clientsocket.close()
        self.log.info('closed')

    def run_cmd(self,bytes):
        '''Some doc about the available commands here:
            * http://www.embecosm.com/appnotes/ean4/embecosm-howto-rsp-server-ean4-issue-2.html#id3081722
            * http://git.qemu.org/?p=qemu.git;a=blob_plain;f=gdbstub.c;h=2b7f22b2d2b8c70af89954294fa069ebf23a5c54;hb=HEAD +
             http://git.qemu.org/?p=qemu.git;a=blob_plain;f=target-i386/gdbstub.c;hb=HEAD'''
        self.log.info('client loop ready...')
        if self.receive(bytes) == 'Good':
            pkt = self.last_pkt
            self.log.debug('receive(%r)' % pkt)
            # Each packet should be acknowledged with a single character. '+' to indicate satisfactory receipt
            self.send_raw('+')

            def handle_q(subcmd):
                '''
                subcmd Supported: https://sourceware.org/gdb/onlinedocs/gdb/General-Query-Packets.html#qSupported
                Report the features supported by the RSP server. As a minimum, just the packet size can be reported.
                '''
                if subcmd.startswith('Supported'):
                    self.log.info('Received qSupported command')
                    self.send('PacketSize=%x' % 4096)
                elif subcmd.startswith('Attached'):
                    self.log.info('Received qAttached command')
                    # https://sourceware.org/gdb/onlinedocs/gdb/General-Query-Packets.html
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
                if subcmd == '':
                    self.log.info('Register Read subcommand')
                    # 32 RISC-V Regigsters
                    registers = []
                    registers = [0 for i in range(33)] 
                    s = ''
                    for r in registers:
                        p = struct.pack('<I', r)
                        for b in p:
                            s += ("{:02X}".format(b))
                        #s += "00000000" # .encode('hex')
                    self.send(s)

            def handle_m(subcmd):
                addr, size = subcmd.split(',')
                addr = int(addr, 16)
                size = int(size, 16)
                self.log.info('Received a "read memory" command (@%#.8x : %d bytes)' % (addr, size))
                #self.send(ReadMemory(size, addr).encode('hex'))

            def handle_s(subcmd):
                self.log.info('Received a "single step" command')
                #StepInto()
                self.send('T%.2x' % GDB_SIGNAL_TRAP)

            dispatchers = {
                'q' : handle_q,
                'H' : handle_h,
                '?' : handle_qmark,
                'g' : handle_g,
                'm' : handle_m,
                's' : handle_s
            }

            cmd, subcmd = pkt[0], pkt[1 :]
            if cmd == 'k':
                pass

            if cmd not in dispatchers:
                self.log.info('%r command not handled' % pkt)
                self.send('')
            else:
                dispatchers[cmd](subcmd)

        

    def receive(self,bytes):
        '''Receive a packet from a GDB client'''
        from io import BytesIO
        # XXX: handle the escaping stuff '}' & (n^0x20)
        csum = 0
        state = 'Finding SOP'
        packet = ''
        self.netin=BytesIO(bytes)
        while True:
            c = self.netin.read(1)
            if c == b'\x03':
                return 'Error: CTRL+C'
            
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
                    packet += c.decode(encoding="ASCII",errors="ignore")
                    csum = (csum + ord(c)) & 0xff               
            else:
                raise Exception('should not be here')

    def send(self, msg):
        '''Send a packet to the GDB client'''
        self.log.debug('send(%r)' % msg)
        self.send_raw('$%s#%.2x' % (msg, checksum(msg)))

    def send_raw(self, r):
        self.netout.write(r)
        self.netout.flush()     

def main():
    logging.basicConfig(level = logging.WARN)
    for logger in 'gdbclienthandler runner main'.split(' '):
        logging.getLogger(logger).setLevel(level = logging.INFO)

    log = logging.getLogger('main')
    port = 31337
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('', port))
    log.info('listening on :%d' % port)
    sock.listen(1)
    conn, addr = sock.accept()
    log.info('connected')

    GDBClientHandler(conn).run()
    return 1

if __name__ == '__main__':
    main()

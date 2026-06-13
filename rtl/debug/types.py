"""
RISC-V debug module — shared types and constants
(c) 2023 The Bonfire Project
License: See LICENSE
"""
from myhdl import enum

t_debugHartState = enum('running', 'halted')
t_abstractCommandType = enum('access_reg', 'quick_access')
# exec, exec2 serve as progbuf pc: exec executes progbuf0 and exec2 executes
# progbuf1 when progbuf_size is 2.  When progbuf_size is 1, exec2 will not be
# used and progbuf0 will be executed in exec state.
t_abstractCommandState = enum('none', 'regvalid', 'taken', 'failed', 'exec', 'exec2', 'wait_retire')

debugSpecVersion = 2  # RISC-V Debug Spec 0.13
csr_depc = 0x7b1
xdedebugver = 4  # RISC-V Debug Spec 0.13

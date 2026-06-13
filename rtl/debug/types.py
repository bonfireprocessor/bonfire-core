"""
RISC-V debug module — shared types and constants
(c) 2023 The Bonfire Project
License: See LICENSE
"""
from myhdl import enum

t_debug_hart_state = enum('running', 'halted')
t_abstract_command_type = enum('access_reg', 'quick_access')
# exec, exec2 serve as progbuf pc: exec executes progbuf0 and exec2 executes
# progbuf1 when progbuf_size is 2.  When progbuf_size is 1, exec2 will not be
# used and progbuf0 will be executed in exec state.
t_abstract_command_state = enum('none', 'regvalid', 'taken', 'failed', 'exec', 'exec2', 'wait_retire')

DEBUG_SPEC_VERSION = 2  # RISC-V Debug Spec 0.13
CSR_DPC = 0x7b1
XDEBUGVER = 4  # RISC-V Debug Spec 0.13

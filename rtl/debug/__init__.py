"""
RISC-V debug subpackage
(c) 2023 The Bonfire Project
License: See LICENSE

Re-exports all public symbols so that code importing from ``rtl.debugModule``
or ``rtl.debug_control`` continues to work unchanged via the compatibility
shims in those modules.
"""
from rtl.debug.types import (
    t_debugHartState,
    t_abstractCommandType,
    t_abstractCommandState,
    debugSpecVersion,
    csr_depc,
    xdedebugver,
)
from rtl.debug.registers import DebugRegisterBundle, AbstractDebugTransportBundle
from rtl.debug.csrs import DebugCSRBundle, DebugCSRUpdateBundle, DebugCSRReadViewBundle
from rtl.debug.dmi import DMI
from rtl.debug.decode_injection import (
    DebugDecodeViewBundle,
    DebugDecodeControlBundle,
    DebugDecodeController,
)

__all__ = [
    # types
    "t_debugHartState",
    "t_abstractCommandType",
    "t_abstractCommandState",
    "debugSpecVersion",
    "csr_depc",
    "xdedebugver",
    # registers
    "DebugRegisterBundle",
    "AbstractDebugTransportBundle",
    # csrs
    "DebugCSRBundle",
    "DebugCSRUpdateBundle",
    "DebugCSRReadViewBundle",
    # dmi
    "DMI",
    # decode injection
    "DebugDecodeViewBundle",
    "DebugDecodeControlBundle",
    "DebugDecodeController",
]

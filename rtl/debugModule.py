"""
RISC-V Hardware Debug Module
(c) 2023 The Bonfire Project
License: See LICENSE

Compatibility shim — all symbols are now in the ``rtl.debug`` subpackage.
"""
# Re-export everything so that existing ``from rtl.debugModule import ...``
# and ``from rtl.debugModule import *`` statements continue to work unchanged.
from rtl.debug import *  # noqa: F401, F403
from rtl.debug import (  # noqa: F401
    t_debugHartState,
    t_abstractCommandType,
    t_abstractCommandState,
    debugSpecVersion,
    csr_depc,
    xdedebugver,
    DebugRegisterBundle,
    AbstractDebugTransportBundle,
    DebugCSRBundle,
    DebugCSRUpdateBundle,
    DebugCSRReadViewBundle,
    DMI,
    DebugDecodeViewBundle,
    DebugDecodeControlBundle,
    DebugDecodeController,
)

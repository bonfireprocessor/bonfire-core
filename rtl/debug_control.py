"""
RISC-V debug control
(c) 2026 The Bonfire Project
License: See LICENSE

Compatibility shim — all symbols are now in ``rtl.debug.decode_injection``.
"""
# Re-export everything so that existing ``from rtl.debug_control import ...``
# and ``from rtl.debug_control import *`` statements continue to work unchanged.
from rtl.debug.decode_injection import *  # noqa: F401, F403
from rtl.debug.decode_injection import (  # noqa: F401
    DebugDecodeViewBundle,
    DebugDecodeControlBundle,
    DebugDecodeController,
)

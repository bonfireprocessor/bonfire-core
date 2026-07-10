"""
RISC-V debug system package
(c) 2023 The Bonfire Project
License: See LICENSE

Exports the Debug Module (DM), Debug Module Interface (DMI), and Debug
Transport Module (DTM) building blocks using names aligned with the RISC-V
debug architecture.
"""
from rtl.debug.types import (
    t_debug_hart_state,
    t_abstract_command_type,
    t_abstract_command_state,
    DEBUG_SPEC_VERSION,
    CSR_DPC,
    XDEBUGVER,
)
from rtl.debug.dm_registers import DebugModuleRegisterBundle, DmiBundle
from rtl.debug.debug_csrs import DebugCSRBundle, DebugCSRUpdateBundle, DebugCSRReadViewBundle
from rtl.debug.dmi import DebugModuleInterface
from rtl.debug.debug_module import (
    DebugHartViewBundle,
    DebugHartControlBundle,
    DebugModuleController,
)
from rtl.debug.jtag_dtm import JtagDTM
from rtl.debug.ecp5_jtagg_client import Ecp5JtaggClient, Ecp5JtaggInputBundle, Ecp5JtaggOutputBundle
from rtl.debug.ecp5_jtagg_tap import Ecp5JtaggTapEmulator

__all__ = [
    # types
    "t_debug_hart_state",
    "t_abstract_command_type",
    "t_abstract_command_state",
    "DEBUG_SPEC_VERSION",
    "CSR_DPC",
    "XDEBUGVER",
    # registers
    "DebugModuleRegisterBundle",
    "DmiBundle",
    # csrs
    "DebugCSRBundle",
    "DebugCSRUpdateBundle",
    "DebugCSRReadViewBundle",
    # dmi
    "DebugModuleInterface",
    # debug module
    "DebugHartViewBundle",
    "DebugHartControlBundle",
    "DebugModuleController",
    # debug transport module
    "JtagDTM",
    "Ecp5JtaggClient",
    "Ecp5JtaggInputBundle",
    "Ecp5JtaggOutputBundle",
    "Ecp5JtaggTapEmulator",
]

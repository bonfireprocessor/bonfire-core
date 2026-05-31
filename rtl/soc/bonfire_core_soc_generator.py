from __future__ import annotations

from typing import Any

from myhdl import Signal, modbv

from rtl import bonfire_interfaces
from rtl.type_aliases import BitSignal


class BonfireCoreSoCInstanceGenerator:
    def __init__(self, soc: Any) -> None:
        self.soc = soc

    def create_instance(self) -> Any:
        sysclk: BitSignal = Signal(bool(0))
        resetn: BitSignal = Signal(bool(1))
        led = Signal(modbv(0)[self.soc.numLeds:])
        uart0_txd: BitSignal = Signal(bool(1))
        uart0_rxd: BitSignal = Signal(bool(0))

        o_resetn: BitSignal = Signal(bool(1))
        i_locked: BitSignal = Signal(bool(0))

        if self.soc.exposeWishboneMaster:
            print("Exposing Wishbone Master Interface")
            wb_master = bonfire_interfaces.Wishbone_master_bundle()
        else:
            wb_master = None

        try:
            return self.soc.bonfire_core_soc(
                sysclk,
                resetn,
                uart0_txd,
                uart0_rxd,
                led,
                o_resetn,
                i_locked,
                wb_master=wb_master,
            )
        except FileNotFoundError as fnf_error:
            print(f"File not found: {fnf_error}")
            import sys
            sys.exit(1)
        except Exception as e:
            print(f"Error initializing bonfire_core_soc: {e}")
            import sys
            sys.exit(1)

    def convert(self, hdl: str, name: str, path: str,
                handleWarnings: str = 'default') -> None:
        from myhdl import ToVHDLWarning
        import warnings

        self.soc.conversion = True
        inst = self.create_instance()

        with warnings.catch_warnings():
            warnings.filterwarnings(
                handleWarnings,
                category=ToVHDLWarning)
            inst.convert(hdl=hdl, std_logic_ports=True, initial_values=True, path=path, name=name)


class BonfireCoreSoCTestbenchGenerator:
    def __init__(self, soc: Any) -> None:
        self.soc = soc

    def create_instance(self) -> Any:
        from tb.soc.bonfire_core_soc_tb import BonfireCoreSoCTestbench

        tb = BonfireCoreSoCTestbench(self.soc, conversion=True)
        return tb.testbench()

    def convert(self, hdl: str, name: str, path: str,
                handleWarnings: str = 'default') -> None:
        from myhdl import ToVHDLWarning
        import warnings

        self.soc.conversion = True
        inst = self.create_instance()

        with warnings.catch_warnings():
            warnings.filterwarnings(
                handleWarnings,
                category=ToVHDLWarning)
            inst.convert(hdl=hdl, std_logic_ports=True, initial_values=True, path=path, name=name)

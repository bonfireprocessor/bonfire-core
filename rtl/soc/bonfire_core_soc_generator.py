from __future__ import annotations

from pathlib import Path
from typing import Any

from myhdl import Signal, modbv

from rtl import bonfire_interfaces
from rtl.type_aliases import BitSignal
from util.diagnostics import diagnostics_context, get_diagnostics


CONVERSION_ELABORATION_QUIET_LEVEL = 1


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
        jtag_tck: BitSignal | None = None
        jtag_tms: BitSignal | None = None
        jtag_tdi: BitSignal | None = None
        jtag_tdo: BitSignal | None = None
        jtag_trstn: BitSignal | None = None

        if self.soc.enableJtagDebug:
            get_diagnostics().detail("soc: exposing JTAG debug interface")
            jtag_tck = Signal(bool(0))
            jtag_tms = Signal(bool(1))
            jtag_tdi = Signal(bool(0))
            jtag_tdo = Signal(bool(0))
            jtag_trstn = Signal(bool(1))

        if self.soc.exposeWishboneMaster:
            get_diagnostics().detail("soc: exposing Wishbone master interface")
            wb_master = bonfire_interfaces.Wishbone_master_bundle()
        else:
            wb_master = None

        try:
            if self.soc.enableJtagDebug:
                return self.soc.bonfire_core_soc(
                    sysclk,
                    resetn,
                    uart0_txd,
                    uart0_rxd,
                    led,
                    o_resetn,
                    i_locked,
                    wb_master=wb_master,
                    jtag_tck=jtag_tck,
                    jtag_tms=jtag_tms,
                    jtag_tdi=jtag_tdi,
                    jtag_tdo=jtag_tdo,
                    jtag_trstn=jtag_trstn,
                )

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
            get_diagnostics().error("file not found: {}".format(fnf_error))
            import sys
            sys.exit(1)
        except Exception as e:
            get_diagnostics().error("initializing bonfire_core_soc: {}".format(e))
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
            with diagnostics_context(
                get_diagnostics().with_quiet_level(CONVERSION_ELABORATION_QUIET_LEVEL)
            ):
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
            with diagnostics_context(
                get_diagnostics().with_quiet_level(CONVERSION_ELABORATION_QUIET_LEVEL)
            ):
                inst.convert(hdl=hdl, std_logic_ports=True, initial_values=True, path=path, name=name)
        if hdl.upper() == "VHDL":
            self._patch_vhdl_stop_simulation(Path(path) / "{}.vhd".format(name))

    def _patch_vhdl_stop_simulation(self, vhdl_file: Path) -> None:
        """Make converted StopSimulation end GHDL runs with exit code 0."""

        text = vhdl_file.read_text()
        text = text.replace(
            "use std.textio.all;\n",
            "use std.textio.all;\nuse std.env.all;\n",
        )
        text = text.replace(
            'assert False report "End of Simulation" severity Failure;',
            'stop;',
        )
        vhdl_file.write_text(text)

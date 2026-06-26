"""
MyHDL wrapper for the Lattice ECP5 JTAGG primitive.
(c) 2026 The Bonfire Project
License: See LICENSE
"""
from __future__ import annotations

from typing import Any

from myhdl import Signal, always_comb, block, instances

from rtl.debug.ecp5_jtagg_client import Ecp5JtaggInputBundle, Ecp5JtaggOutputBundle
from rtl.type_aliases import BitSignal


ECP5_JTAGG_VHDL_CODE = """
u_jtagg: entity work.JTAGG
    port map (
        JTDO2   => $jtdo2,
        JTDO1   => $jtdo1,
        JTDI    => $jtdi,
        JTCK    => $jtck,
        JRT2    => $jrt2,
        JRT1    => $jrt1,
        JSHIFT  => $jshift,
        JUPDATE => $jupdate,
        JRSTN   => $jrstn,
        JCE2    => $jce2,
        JCE1    => $jce1
    );
"""


@block(vhdl_code=ECP5_JTAGG_VHDL_CODE)
def Ecp5JtaggPrimitive(
    jtck: BitSignal,
    jtdi: BitSignal,
    jshift: BitSignal,
    jupdate: BitSignal,
    jrstn: BitSignal,
    jce1: BitSignal,
    jce2: BitSignal,
    jrt1: BitSignal,
    jrt2: BitSignal,
    jtdo1: BitSignal,
    jtdo2: BitSignal,
) -> Any:
    name_anchor = Signal(bool(0))

    jrstn.driven = True
    jce1.driven = True
    jce2.driven = True
    jrt1.driven = True
    jrt2.driven = True
    jtdi.driven = True
    jshift.driven = True
    jtck.driven = True
    jupdate.driven = True

    @always_comb
    def collect_signal_names():
        name_anchor.next = (
            jtck or jtdi or jshift or jupdate or jrstn or jce1 or jce2
            or jrt1 or jrt2 or jtdo1 or jtdo2
        )

    return instances()


@block
def Ecp5JtaggPrimitiveForBundle(
    jtagg_i: Ecp5JtaggInputBundle,
    jtagg_o: Ecp5JtaggOutputBundle,
) -> Any:
    jtagg_jtck = jtagg_i.jtck
    jtagg_jtdi = jtagg_i.jtdi
    jtagg_jshift = jtagg_i.jshift
    jtagg_jupdate = jtagg_i.jupdate
    jtagg_jrstn = jtagg_i.jrstn
    jtagg_jce1 = jtagg_i.jce1
    jtagg_jce2 = jtagg_i.jce2
    jtagg_jrt1 = jtagg_i.jrt1
    jtagg_jrt2 = jtagg_i.jrt2
    jtagg_jtdo1 = jtagg_o.jtdo1
    jtagg_jtdo2 = jtagg_o.jtdo2
    primitive = Ecp5JtaggPrimitive(
        jtagg_jtck,
        jtagg_jtdi,
        jtagg_jshift,
        jtagg_jupdate,
        jtagg_jrstn,
        jtagg_jce1,
        jtagg_jce2,
        jtagg_jrt1,
        jtagg_jrt2,
        jtagg_jtdo1,
        jtagg_jtdo2,
    )

    return instances()

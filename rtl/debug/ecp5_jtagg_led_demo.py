"""
Small ECP5 JTAGG USER-register LED proof of concept.
(c) 2026 The Bonfire Project
License: See LICENSE
"""
from __future__ import annotations

from typing import Any

from myhdl import Signal, always, always_comb, block, concat, instances, modbv

from rtl.debug.ecp5_jtagg_client import Ecp5JtaggInputBundle, Ecp5JtaggOutputBundle
from rtl.type_aliases import BitSignal


@block
def Ecp5JtaggLedDemo(
    led: Any,
    jtagg_i: Ecp5JtaggInputBundle,
    jtagg_o: Ecp5JtaggOutputBundle,
) -> Any:
    width = len(led)
    assert width > 0, "Ecp5JtaggLedDemo requires at least one LED"

    shift_reg = Signal(modbv(0)[width:])
    led_reg = Signal(modbv(0)[width:])
    active_er1: BitSignal = Signal(bool(0))

    @always(jtagg_i.jtck.posedge)
    def shift_user_register():
        if not jtagg_i.jrstn:
            shift_reg.next = 0
            active_er1.next = False
        elif jtagg_i.jce1:
            active_er1.next = True
            if jtagg_i.jshift:
                shift_reg.next = concat(jtagg_i.jtdi, shift_reg[width:1])
        elif jtagg_i.jce2:
            active_er1.next = False
        elif jtagg_i.jrt1:
            active_er1.next = True
        elif jtagg_i.jrt2:
            active_er1.next = False

    @always(jtagg_i.jupdate.posedge)
    def update_leds():
        if not jtagg_i.jrstn:
            led_reg.next = 0
        elif active_er1:
            led_reg.next = shift_reg

    @always_comb
    def outputs():
        led.next = led_reg
        jtagg_o.jtdo1.next = shift_reg[0]
        jtagg_o.jtdo2.next = False

    return instances()

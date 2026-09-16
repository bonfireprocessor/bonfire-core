"""Tests for the isolated four-stage cascaded RV32 multiplier."""

from __future__ import annotations

import random

import pytest
from myhdl import ResetSignal, Signal, StopSimulation, always, block, delay, instance

from rtl.multiplier import MultiplierBundle
from tests.conftest import run_sim


MASK32 = 0xFFFFFFFF
MASK64 = 0xFFFFFFFFFFFFFFFF


def _signed32(value: int) -> int:
    value &= MASK32
    return value - (1 << 32) if value & (1 << 31) else value


def _reference(
    op1: int,
    op2: int,
    signed_a: bool,
    signed_b: bool,
    high: bool,
) -> int:
    lhs = _signed32(op1) if signed_a else op1 & MASK32
    rhs = _signed32(op2) if signed_b else op2 & MASK32
    product = (lhs * rhs) & MASK64
    return (product >> 32 if high else product) & MASK32


CORNER_OPERANDS = [
    0,
    1,
    2,
    0x7FFF,
    0x8000,
    0xFFFF,
    0x10000,
    0x7FFFFFFF,
    0x80000000,
    0xFFFFFFFE,
    0xFFFFFFFF,
]


def _vectors() -> list[tuple[int, int, bool, bool, bool]]:
    cases = []
    modes = [
        (False, False, False),  # MUL low word
        (True, True, True),     # MULH
        (True, False, True),    # MULHSU
        (False, False, True),   # MULHU
    ]
    for signed_a, signed_b, high in modes:
        for op1 in CORNER_OPERANDS:
            for op2 in CORNER_OPERANDS:
                cases.append((op1, op2, signed_a, signed_b, high))

    rng = random.Random(0xB0F1_32)
    for _ in range(400):
        signed_a, signed_b, high = modes[rng.randrange(len(modes))]
        cases.append((
            rng.getrandbits(32),
            rng.getrandbits(32),
            signed_a,
            signed_b,
            high,
        ))
    return cases


@block
def multiplier_testbench(vectors):
    clock = Signal(bool(0))
    reset = ResetSignal(0, active=1, isasync=False)
    multiplier = MultiplierBundle()
    dut = multiplier.multiplier(clock, reset)

    @always(delay(5))
    def clock_gen():
        clock.next = not clock

    @instance
    def stimulus():
        multiplier.ce_i.next = False
        reset.next = True
        yield clock.posedge
        yield delay(1)
        assert not multiplier.ce_o
        reset.next = False

        expected = []
        schedule = list(vectors) + [None, None, None, None]

        for item in schedule:
            yield clock.negedge
            if item is None:
                multiplier.ce_i.next = False
                current = None
            else:
                op1, op2, signed_a, signed_b, high = item
                multiplier.op1_i.next = op1
                multiplier.op2_i.next = op2
                multiplier.signed_a_i.next = signed_a
                multiplier.signed_b_i.next = signed_b
                multiplier.high_i.next = high
                multiplier.ce_i.next = True
                current = _reference(op1, op2, signed_a, signed_b, high)

            yield clock.posedge
            yield delay(1)
            expected.append(current)
            due = expected.pop(0) if len(expected) >= 4 else None
            assert bool(multiplier.ce_o) == (due is not None)
            if due is not None:
                assert int(multiplier.result_o) == due

        multiplier.ce_i.next = False
        raise StopSimulation

    return dut, clock_gen, stimulus


@block
def multiplier_reset_testbench():
    clock = Signal(bool(0))
    reset = ResetSignal(0, active=1, isasync=False)
    multiplier = MultiplierBundle()
    dut = multiplier.multiplier(clock, reset)

    @always(delay(5))
    def clock_gen():
        clock.next = not clock

    @instance
    def stimulus():
        multiplier.ce_i.next = False
        reset.next = True
        yield clock.posedge
        reset.next = False

        # Fill the first three stages, then reset before any result becomes
        # visible.  Reset cancels validity without requiring wide data resets.
        for value in (3, 5, 7):
            yield clock.negedge
            multiplier.op1_i.next = value
            multiplier.op2_i.next = value + 1
            multiplier.ce_i.next = True
            yield clock.posedge

        yield clock.negedge
        multiplier.ce_i.next = False
        reset.next = True
        yield clock.posedge
        yield delay(1)
        assert not multiplier.ce_o
        reset.next = False

        for _ in range(4):
            yield clock.posedge
            yield delay(1)
            assert not multiplier.ce_o

        # The pipeline remains usable and preserves the documented latency.
        yield clock.negedge
        multiplier.op1_i.next = 0x12345678
        multiplier.op2_i.next = 0x10
        multiplier.high_i.next = False
        multiplier.ce_i.next = True
        yield clock.posedge
        yield delay(1)
        assert not multiplier.ce_o

        multiplier.ce_i.next = False
        for cycle in range(1, 4):
            yield clock.posedge
            yield delay(1)
            assert bool(multiplier.ce_o) == (cycle == 3)

        assert int(multiplier.result_o) == 0x23456780
        raise StopSimulation

    return dut, clock_gen, stimulus


def test_multiplier_corner_random_latency_and_throughput(sim_env):
    vectors = _vectors()
    run_sim(
        multiplier_testbench(vectors),
        trace=True,
        waveforms_dir=sim_env["waveforms_dir"],
        duration=20000,
        filename="multiplier",
    )


def test_multiplier_rejects_non_rv32_width():
    with pytest.raises(AssertionError, match="RV32"):
        MultiplierBundle(xlen=64)


def test_multiplier_reset_cancels_inflight_results(sim_env):
    run_sim(
        multiplier_reset_testbench(),
        trace=False,
        waveforms_dir=sim_env["waveforms_dir"],
        duration=1000,
        filename="multiplier_reset",
    )

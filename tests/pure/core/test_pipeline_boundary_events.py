from __future__ import annotations

import pytest
from myhdl import Simulation, StopSimulation, always, block, delay, instance

from rtl.bonfire_interfaces import (
    PIPELINE_SOURCE_DEBUG_REGISTER,
    PIPELINE_SOURCE_NORMAL,
    PIPELINE_SOURCE_PROGRAM_BUFFER,
    PipelineBoundaryEventAssertions,
    PipelineBoundaryEventBundle,
)
from rtl.config import BonfireConfig


def test_pipeline_boundary_event_bundle_defaults():
    config = BonfireConfig()
    config.reset_address = 0x1000
    events = PipelineBoundaryEventBundle(config)

    assert len(events.source) == 2
    assert len(events.accepted_source) == 2
    assert len(events.accepted_pc) == config.xlen
    assert len(events.instruction_pc) == config.xlen
    assert len(events.next_pc) == config.xlen
    assert len(events.redirect_pc) == config.xlen
    assert len(events.register_address) == 5
    assert len(events.register_data) == config.xlen
    assert int(events.source) == PIPELINE_SOURCE_NORMAL
    assert int(events.next_pc) == config.reset_address
    assert events.pipeline_empty
    assert events.drained

    assert {
        PIPELINE_SOURCE_NORMAL,
        PIPELINE_SOURCE_PROGRAM_BUFFER,
        PIPELINE_SOURCE_DEBUG_REGISTER,
    } == {0, 1, 2}


def _run_assertion_case(assign):
    events = PipelineBoundaryEventBundle(BonfireConfig())

    @block
    def bench():
        assertions = PipelineBoundaryEventAssertions(events)

        @instance
        def stimulus():
            assign(events)
            yield delay(1)
            raise StopSimulation

        return assertions, stimulus

    Simulation(bench()).run()


def test_pipeline_boundary_event_assertions_accept_valid_outcomes():
    def completed(events):
        events.valid.next = True
        events.terminal.next = True
        events.completed.next = True
        events.retired.next = True
        events.register_write.next = True

    def trapped(events):
        events.valid.next = True
        events.terminal.next = True
        events.exception.next = True
        events.trap.next = True

    def cancelled(events):
        events.valid.next = True
        events.terminal.next = True
        events.cancelled.next = True
        events.killed.next = True

    for assign in (completed, trapped, cancelled):
        _run_assertion_case(assign)


@pytest.mark.parametrize(
    "assign",
    (
        lambda events: (
            setattr(events.terminal, "next", True),
            setattr(events.completed, "next", True),
            setattr(events.exception, "next", True),
        ),
        lambda events: setattr(events.terminal, "next", True),
        lambda events: (
            setattr(events.terminal, "next", True),
            setattr(events.completed, "next", True),
        ),
        lambda events: (
            setattr(events.valid, "next", True),
            setattr(events.source, "next", 3),
        ),
        lambda events: setattr(events.retired, "next", True),
        lambda events: setattr(events.trap, "next", True),
        lambda events: setattr(events.killed, "next", True),
        lambda events: setattr(events.register_write, "next", True),
        lambda events: setattr(events.store_commit, "next", True),
        lambda events: setattr(events.drained, "next", False),
    ),
    ids=(
        "multiple-outcomes",
        "terminal-without-outcome",
        "terminal-without-valid-metadata",
        "reserved-source",
        "retire-without-completion",
        "trap-without-exception",
        "kill-without-cancel",
        "write-without-retirement",
        "store-without-retirement",
        "empty-without-drained",
    ),
)
def test_pipeline_boundary_event_assertions_reject_invalid_events(assign):
    with pytest.raises(AssertionError):
        _run_assertion_case(assign)

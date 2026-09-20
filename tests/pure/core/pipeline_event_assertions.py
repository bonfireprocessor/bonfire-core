"""MyHDL assertion helper used only by pipeline-event tests."""

from typing import Any

from myhdl import always_comb, block, instances

from rtl.pipeline_events import PipelineBoundaryEventBundle


@block
def PipelineBoundaryEventAssertions(events: PipelineBoundaryEventBundle) -> Any:
    """Check local invariants for a driven pipeline-boundary event bundle."""

    @always_comb
    def check():
        terminal_outcomes = int(events.completed) + int(events.exception) + \
            int(events.cancelled)

        assert terminal_outcomes <= 1, \
            "pipeline boundary has multiple terminal outcomes"
        assert bool(events.terminal) == (terminal_outcomes == 1), \
            "pipeline terminal must identify exactly one outcome"
        assert not events.terminal or events.valid, \
            "a terminal event must carry valid metadata"
        assert not events.accepted or events.accepted_source != 3, \
            "accepted pipeline event source is reserved"
        assert not events.valid or events.source != 3, \
            "pipeline event source is reserved"
        assert not events.retired or events.completed, \
            "only a successfully completed operation may retire"
        assert not events.trap or events.exception, \
            "a trap event must be an exception outcome"
        assert not events.killed or events.cancelled, \
            "a killed operation must be cancelled"
        assert not events.register_write or events.retired, \
            "register write requires retirement"
        assert not events.store_commit or events.retired, \
            "store commit requires retirement"
        assert not events.pipeline_empty or events.drained, \
            "an empty pipeline must be drained"

    return instances()

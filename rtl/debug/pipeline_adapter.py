"""Pipeline boundary used by the optional RISC-V debug module."""

from __future__ import annotations

from typing import Any

from myhdl import Signal, always, always_comb, block, instances, modbv

from rtl.debug.abstract_command import ProgbufCompletionBundle, ProgbufIssueBundle


PROGBUF_EBREAK = 0x00100073


class DebugPipelineRequestBundle:
    """Requests from hart debug control to the pipeline."""

    def __init__(self, config: Any) -> None:
        self.allow_fetch = Signal(bool(1))
        self.flush = Signal(bool(0))
        self.redirect_valid = Signal(bool(0))
        self.redirect_pc = Signal(modbv(0)[config.xlen:])


class DebugPipelineEventBundle:
    """Architectural pipeline boundary events observed by debug control."""

    def __init__(self, config: Any) -> None:
        self.instruction_accepted = Signal(bool(0))
        self.instruction_complete = Signal(bool(0))
        self.pipeline_empty = Signal(bool(1))
        self.next_pc = Signal(modbv(config.reset_address)[config.xlen:])
        self.ebreak = Signal(bool(0))
        self.ebreak_pc = Signal(modbv(0)[config.xlen:])
        self.progbuf_exception = Signal(bool(0))


@block
def DebugPipelineAdapter(
    config: Any,
    clock: Any,
    fetch_bundle: Any,
    fetch_stage: Any,
    decode: Any,
    request: DebugPipelineRequestBundle,
    events: DebugPipelineEventBundle,
    progbuf_issue: ProgbufIssueBundle,
    progbuf_completion: ProgbufCompletionBundle,
    pipeline_empty_i: Any,
    execute_redirect_valid_i: Any,
    execute_redirect_pc_i: Any,
    ebreak_i: Any,
    ebreak_pc_i: Any,
    progbuf_exception_i: Any,
    progbuf_active_o: Any,
) -> Any:
    """Select Fetch or Program Buffer and track one architectural boundary."""

    active = Signal(bool(0))
    active_progbuf = Signal(bool(0))
    architectural_next_pc = Signal(modbv(config.reset_address)[config.xlen:])
    source_accepted = Signal(bool(0))
    source_progbuf = Signal(bool(0))

    @always_comb
    def source_mux():
        progbuf_terminator = progbuf_issue.valid and \
            progbuf_issue.word == PROGBUF_EBREAK
        progbuf_source = progbuf_issue.valid and not progbuf_terminator
        source_valid = fetch_bundle.en_i and request.allow_fetch and \
            not fetch_bundle.redirect_pending_i and not request.redirect_valid

        decode.word_i.next = fetch_bundle.word_i
        decode.current_ip_i.next = fetch_bundle.current_ip_i
        decode.next_ip_i.next = fetch_bundle.next_ip_i

        if progbuf_issue.valid:
            decode.word_i.next = progbuf_issue.word
            source_valid = not progbuf_terminator

        accepted = source_valid and not decode.busy_o
        complete = active and pipeline_empty_i
        next_pc = architectural_next_pc
        if active and not active_progbuf and execute_redirect_valid_i:
            next_pc = execute_redirect_pc_i

        decode.en_i.next = source_valid
        source_accepted.next = accepted
        source_progbuf.next = progbuf_source
        fetch_stage.stall_i.next = decode.busy_o or not request.allow_fetch or \
            request.redirect_valid or progbuf_issue.valid

        events.instruction_accepted.next = accepted and not progbuf_source
        events.instruction_complete.next = complete and not active_progbuf
        events.pipeline_empty.next = pipeline_empty_i
        events.next_pc.next = next_pc
        events.ebreak.next = ebreak_i
        events.ebreak_pc.next = ebreak_pc_i
        events.progbuf_exception.next = active and active_progbuf and progbuf_exception_i

        progbuf_completion.accepted.next = accepted and progbuf_source
        progbuf_completion.complete.next = complete and active_progbuf and not progbuf_exception_i
        progbuf_completion.terminated.next = progbuf_terminator
        progbuf_completion.exception.next = active and active_progbuf and progbuf_exception_i
        progbuf_active_o.next = active_progbuf

    @always(clock.posedge)
    def boundary_tracker():
        if source_accepted:
            active.next = True
            active_progbuf.next = source_progbuf

        if request.redirect_valid:
            architectural_next_pc.next = request.redirect_pc
        elif source_accepted and not source_progbuf:
            architectural_next_pc.next = decode.next_ip_i
        elif active and not active_progbuf and execute_redirect_valid_i:
            architectural_next_pc.next = execute_redirect_pc_i

        if active and (pipeline_empty_i or (active_progbuf and progbuf_exception_i)):
            active.next = False
            active_progbuf.next = False

    return instances()

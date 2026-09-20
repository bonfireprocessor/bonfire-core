"""
Pipeline Boundary Used by the Optional RISC-V Debug Module
(c) 2026 The Bonfire Project
License: See LICENSE

Pipeline boundary used by the optional RISC-V debug module.
"""

from __future__ import annotations

from typing import Any

from myhdl import Signal, always_comb, always_seq, block, instances, modbv

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
        self.instruction_exception = Signal(bool(0))
        self.exception_next_pc = Signal(modbv(config.reset_address)[config.xlen:])
        self.pipeline_empty = Signal(bool(1))
        self.next_pc = Signal(modbv(config.reset_address)[config.xlen:])
        self.ebreak = Signal(bool(0))
        self.ebreak_pc = Signal(modbv(0)[config.xlen:])
        self.progbuf_exception = Signal(bool(0))


@block
def DebugPipelineAdapter(
    config: Any,
    clock: Any,
    reset: Any,
    fetch_bundle: Any,
    fetch_stage: Any,
    decode: Any,
    request: DebugPipelineRequestBundle,
    events: DebugPipelineEventBundle,
    progbuf_issue: ProgbufIssueBundle,
    progbuf_completion: ProgbufCompletionBundle,
    boundary_events: Any,
    trap_vector_i: Any,
    ebreak_i: Any,
    ebreak_pc_i: Any,
    progbuf_exception_i: Any,
    progbuf_active_o: Any,
) -> Any:
    """Select Fetch or Program Buffer and track one architectural boundary."""

    active = Signal(bool(0))
    active_progbuf = Signal(bool(0))
    pipeline_empty = Signal(bool(1))
    source_accepted = Signal(bool(0))
    source_progbuf = Signal(bool(0))
    instruction_exception = Signal(bool(0))
    progbuf_exception = Signal(bool(0))
    progbuf_pending = Signal(bool(0))
    progbuf_word = Signal(modbv(0)[config.xlen:])

    @always_comb
    def source_mux():
        # Program Buffer requests cross a register boundary before Decode.
        # This removes the abstract-command state/word mux from Decode's
        # acceptance and metadata-register enable paths.
        progbuf_terminator = progbuf_pending and \
            progbuf_word == PROGBUF_EBREAK
        progbuf_source = progbuf_pending and not progbuf_terminator
        source_valid = fetch_bundle.en_i and request.allow_fetch and \
            not fetch_bundle.redirect_pending_i and not request.redirect_valid

        decode.word_i.next = fetch_bundle.word_i
        decode.current_ip_i.next = fetch_bundle.current_ip_i
        decode.next_ip_i.next = fetch_bundle.next_ip_i

        if progbuf_pending:
            decode.word_i.next = progbuf_word
            source_valid = not progbuf_terminator and not progbuf_exception

        accepted = source_valid and not decode.busy_o
        normal_complete = active and boundary_events.completed

        decode.en_i.next = source_valid
        source_accepted.next = accepted
        source_progbuf.next = progbuf_source
        fetch_stage.stall_i.next = decode.busy_o or not request.allow_fetch or \
            request.redirect_valid or progbuf_issue.valid or progbuf_pending

        events.instruction_accepted.next = accepted and not progbuf_source
        events.instruction_complete.next = normal_complete and not active_progbuf
        events.instruction_exception.next = instruction_exception
        events.exception_next_pc.next = trap_vector_i
        events.pipeline_empty.next = pipeline_empty
        events.next_pc.next = boundary_events.next_pc
        events.ebreak.next = ebreak_i
        events.ebreak_pc.next = ebreak_pc_i
        events.progbuf_exception.next = progbuf_exception

        progbuf_completion.accepted.next = accepted and progbuf_source
        progbuf_completion.complete.next = active and active_progbuf and \
            boundary_events.completed
        progbuf_completion.terminated.next = progbuf_terminator
        progbuf_completion.exception.next = progbuf_exception
        progbuf_active_o.next = active_progbuf

    @always_seq(clock.posedge, reset=reset)
    def boundary_tracker():
        # Halting may wait one extra cycle; keeping the drain indication
        # registered prevents Execute result qualification from becoming a
        # debug CSR write-enable path.
        pipeline_empty.next = boundary_events.pipeline_empty
        instruction_exception.next = active and \
            boundary_events.exception and not active_progbuf
        progbuf_exception.next = active and active_progbuf and \
            progbuf_exception_i
        if not progbuf_pending and progbuf_issue.valid:
            progbuf_pending.next = True
            progbuf_word.next = progbuf_issue.word
        if (source_accepted and source_progbuf) or \
                (progbuf_pending and progbuf_word == PROGBUF_EBREAK):
            progbuf_pending.next = False
        if source_accepted:
            active.next = True
            active_progbuf.next = source_progbuf

        if (active and boundary_events.completed) or instruction_exception or \
                progbuf_exception:
            active.next = False
            active_progbuf.next = False

    return instances()

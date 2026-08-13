"""Pipeline boundary used by the optional RISC-V debug module."""

from __future__ import annotations

from typing import Any

from myhdl import Signal, always, always_comb, block, instances, modbv

from rtl.debug.abstract_command import ProgramBufferCompletionBundle, ProgramBufferIssueBundle


PROGRAM_BUFFER_EBREAK = 0x00100073


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
        self.accepted_pc = Signal(modbv(0)[config.xlen:])
        self.instruction_complete = Signal(bool(0))
        self.completion_program_buffer = Signal(bool(0))
        self.pipeline_empty = Signal(bool(1))
        self.architectural_pc = Signal(modbv(config.reset_address)[config.xlen:])
        self.completed_pc = Signal(modbv(0)[config.xlen:])
        self.next_pc = Signal(modbv(0)[config.xlen:])
        self.ebreak = Signal(bool(0))
        self.ebreak_pc = Signal(modbv(0)[config.xlen:])


@block
def DebugPipelineAdapter(
    config: Any,
    clock: Any,
    fetch_bundle: Any,
    fetch_stage: Any,
    decode: Any,
    request: DebugPipelineRequestBundle,
    events: DebugPipelineEventBundle,
    program_issue: ProgramBufferIssueBundle,
    program_completion: ProgramBufferCompletionBundle,
    pipeline_empty_i: Any,
    execute_redirect_valid_i: Any,
    execute_redirect_pc_i: Any,
    ebreak_i: Any,
    ebreak_pc_i: Any,
) -> Any:
    """Select Fetch or Program Buffer and track one architectural boundary."""

    active = Signal(bool(0))
    active_program_buffer = Signal(bool(0))
    active_pc = Signal(modbv(0)[config.xlen:])
    resolved_next_pc = Signal(modbv(config.reset_address)[config.xlen:])
    source_accepted = Signal(bool(0))
    source_program_buffer = Signal(bool(0))

    @always_comb
    def source_mux():
        program_terminator = program_issue.valid and \
            program_issue.word == PROGRAM_BUFFER_EBREAK
        program_source = program_issue.valid and not program_terminator
        source_valid = fetch_bundle.en_i and request.allow_fetch and \
            not fetch_bundle.redirect_pending_i and not request.redirect_valid

        decode.word_i.next = fetch_bundle.word_i
        decode.current_ip_i.next = fetch_bundle.current_ip_i
        decode.next_ip_i.next = fetch_bundle.next_ip_i

        if program_issue.valid:
            decode.word_i.next = program_issue.word
            decode.current_ip_i.next = program_issue.pc
            decode.next_ip_i.next = program_issue.pc + 4
            source_valid = not program_terminator

        accepted = source_valid and not decode.busy_o
        complete = active and pipeline_empty_i
        next_pc = resolved_next_pc
        if active and execute_redirect_valid_i:
            next_pc = execute_redirect_pc_i

        decode.en_i.next = source_valid
        source_accepted.next = accepted
        source_program_buffer.next = program_source
        fetch_stage.stall_i.next = decode.busy_o or not request.allow_fetch or \
            request.redirect_valid or program_issue.valid

        events.instruction_accepted.next = accepted
        events.accepted_pc.next = decode.current_ip_i
        events.instruction_complete.next = complete
        events.completion_program_buffer.next = active_program_buffer
        events.pipeline_empty.next = pipeline_empty_i
        events.architectural_pc.next = resolved_next_pc
        events.completed_pc.next = active_pc
        events.next_pc.next = next_pc
        events.ebreak.next = ebreak_i
        events.ebreak_pc.next = ebreak_pc_i

        program_completion.accepted.next = accepted and program_source
        program_completion.complete.next = complete and active_program_buffer
        program_completion.terminated.next = program_terminator

    @always(clock.posedge)
    def boundary_tracker():
        if source_accepted:
            active.next = True
            active_program_buffer.next = source_program_buffer
            active_pc.next = decode.current_ip_i
            resolved_next_pc.next = decode.next_ip_i
        elif active and execute_redirect_valid_i:
            resolved_next_pc.next = execute_redirect_pc_i

        if active and pipeline_empty_i:
            active.next = False
            active_program_buffer.next = False

    return instances()

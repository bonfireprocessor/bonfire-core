"""RISC-V abstract-command and Program Buffer control."""

from __future__ import annotations

from typing import Any

from myhdl import Signal, always, always_comb, block, instances, modbv

from rtl.debug.dm_registers import DebugModuleRegisterBundle
from rtl.debug.types import t_abstract_command_state, t_abstract_command_type, t_debug_hart_state


class AbstractRegisterTransferBundle:
    """Abstract GPR transfer request presented to the decode/register path."""

    def __init__(self, config: Any) -> None:
        self.valid = Signal(bool(0))
        self.write = Signal(bool(0))
        self.regno = Signal(modbv(0)[5:])
        self.write_data = Signal(modbv(0)[config.xlen:])
        self.read_data = Signal(modbv(0)[config.xlen:])


class ProgbufIssueBundle:
    """One Program Buffer instruction offered to the pipeline adapter."""

    def __init__(self, config: Any) -> None:
        self.valid = Signal(bool(0))
        self.word = Signal(modbv(0)[config.xlen:])
        self.last = Signal(bool(0))


class ProgbufCompletionBundle:
    """Pipeline acknowledgement and completion of a Program Buffer word."""

    def __init__(self) -> None:
        self.accepted = Signal(bool(0))
        self.complete = Signal(bool(0))
        self.terminated = Signal(bool(0))
        self.exception = Signal(bool(0))


@block
def AbstractCommandController(
    config: Any,
    clock: Any,
    debug_regs: DebugModuleRegisterBundle,
    register_transfer: AbstractRegisterTransferBundle,
    progbuf_issue: ProgbufIssueBundle,
    progbuf_completion: ProgbufCompletionBundle,
) -> Any:
    """Execute abstract GPR transfers and sequence Program Buffer words."""

    command_request = Signal(bool(0))
    issued_last = Signal(bool(0))

    @always_comb
    def outputs():
        command_request.next = (
            debug_regs.abstract_command_new and
            debug_regs.abstract_command_state == t_abstract_command_state.none and
            debug_regs.command_type == t_abstract_command_type.access_reg
        )

        register_transfer.valid.next = command_request and debug_regs.transfer
        register_transfer.write.next = debug_regs.write
        register_transfer.regno.next = debug_regs.regno
        register_transfer.write_data.next = debug_regs.data_regs[0]

        progbuf_issue.valid.next = (
            debug_regs.abstract_command_state == t_abstract_command_state.exec or
            debug_regs.abstract_command_state == t_abstract_command_state.exec2
        )
        if debug_regs.abstract_command_state == t_abstract_command_state.exec2:
            progbuf_issue.word.next = debug_regs.progbuf1
            progbuf_issue.last.next = True
        else:
            progbuf_issue.word.next = debug_regs.progbuf0
            progbuf_issue.last.next = config.progbuf_size == 1

    @always(clock.posedge)
    def state_machine():
        if not debug_regs.dmactive:
            debug_regs.abstract_command_state.next = t_abstract_command_state.none
            issued_last.next = False
        elif debug_regs.hart_state == t_debug_hart_state.halted:
            if debug_regs.abstract_command_state == t_abstract_command_state.none:
                if command_request:
                    debug_regs.abstract_command_state.next = t_abstract_command_state.taken

            elif debug_regs.abstract_command_state == t_abstract_command_state.taken:
                if debug_regs.transfer and debug_regs.write:
                    if debug_regs.postexec:
                        debug_regs.abstract_command_state.next = t_abstract_command_state.exec
                    else:
                        debug_regs.abstract_command_state.next = t_abstract_command_state.none
                elif debug_regs.transfer:
                    debug_regs.abstract_command_result.next = register_transfer.read_data
                    debug_regs.abstract_command_state.next = t_abstract_command_state.regvalid
                elif debug_regs.postexec:
                    debug_regs.abstract_command_state.next = t_abstract_command_state.exec
                else:
                    debug_regs.abstract_command_state.next = t_abstract_command_state.none

            elif debug_regs.abstract_command_state == t_abstract_command_state.regvalid:
                if debug_regs.postexec:
                    debug_regs.abstract_command_state.next = t_abstract_command_state.exec
                else:
                    debug_regs.abstract_command_state.next = t_abstract_command_state.none

            elif debug_regs.abstract_command_state == t_abstract_command_state.exec or \
                 debug_regs.abstract_command_state == t_abstract_command_state.exec2:
                if progbuf_completion.terminated:
                    debug_regs.abstract_command_state.next = t_abstract_command_state.none
                elif progbuf_completion.accepted:
                    issued_last.next = progbuf_issue.last
                    debug_regs.abstract_command_state.next = t_abstract_command_state.wait_retire

            elif debug_regs.abstract_command_state == t_abstract_command_state.wait_retire:
                if progbuf_completion.exception:
                    debug_regs.abstract_command_state.next = t_abstract_command_state.failed
                elif progbuf_completion.complete:
                    if issued_last:
                        debug_regs.abstract_command_state.next = t_abstract_command_state.none
                    else:
                        debug_regs.abstract_command_state.next = t_abstract_command_state.exec2

            elif debug_regs.abstract_command_state == t_abstract_command_state.failed:
                debug_regs.abstract_command_state.next = t_abstract_command_state.none

    return instances()

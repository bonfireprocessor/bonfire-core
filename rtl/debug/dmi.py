"""
RISC-V debug module — DMI interface and abstract command protocol
(c) 2023 The Bonfire Project
License: See LICENSE
"""
from __future__ import annotations

from typing import Any

from myhdl import block, always, instances

from rtl.debug.dm_registers import DebugModuleRegisterBundle, DmiBundle
from rtl.debug.types import (
    t_abstract_command_state,
    t_abstract_command_type,
    t_debug_hart_state,
    DEBUG_SPEC_VERSION,
)
from rtl.type_aliases import BitSignal
from util.diagnostics import get_diagnostics


class DebugModuleInterface:
    def __init__(self, config: Any) -> None:
        self.config = config
        xlen = config.xlen
        self.xlen = xlen

    @block
    def dmi_interface(
        self,
        dtm: DmiBundle,
        debugRegs: DebugModuleRegisterBundle,
        clock: BitSignal,
    ) -> Any:
        """
        dtm: DmiBundle
        debugRegs: DebugModuleRegisterBundle
        """
        get_diagnostics().detail("dmi_interface: numdata={} progbuf_size={} dmi_adr_width={}".format(
            self.config.numdata,
            self.config.progbuf_size,
            self.config.dmi_adr_width,
        ))

        @always(clock.posedge)
        def seq():

            if debugRegs.req_ack:
                if debugRegs.resumereq:
                    debugRegs.resumeack.next = True

                debugRegs.haltreq.next = False
                debugRegs.resumereq.next = False

            # Abstract Command execution management
            if debugRegs.abstract_command_state == t_abstract_command_state.regvalid:
                debugRegs.data_regs[0].next = debugRegs.abstract_command_result
            elif debugRegs.abstract_command_state == t_abstract_command_state.taken:
                debugRegs.abstract_command_new.next = False

            dtm.dbo.next = 0
            if dtm.en:
                if not dtm.we:
                    if dtm.adr == 0x11:  # dmstatus
                        dtm.dbo.next[22] = True  # impbreak
                        dtm.dbo.next[17] = debugRegs.resumeack  # allresumeack
                        dtm.dbo.next[16] = debugRegs.resumeack  # anyresumeack
                        dtm.dbo.next[11] = debugRegs.hart_state == t_debug_hart_state.running  # allrunning
                        dtm.dbo.next[10] = debugRegs.hart_state == t_debug_hart_state.running  # anyrunning
                        dtm.dbo.next[9] = debugRegs.hart_state == t_debug_hart_state.halted  # allhalted
                        dtm.dbo.next[8] = debugRegs.hart_state == t_debug_hart_state.halted  # anyhalted
                        dtm.dbo.next[7] = True  # authenticated
                        dtm.dbo.next[4:] = DEBUG_SPEC_VERSION  # version
                    elif dtm.adr == 0x10:  # dmcontrol
                        dtm.dbo.next[1] = debugRegs.hart_reset  # ndmreset
                        dtm.dbo.next[0] = True
                    elif dtm.adr == 0x12:  # hartinfo
                        dtm.dbo.next[24:20] = self.config.num_dscratch
                        dtm.dbo.next[16:12] = self.config.numdata
                    elif dtm.adr == 0x18:  # abstractauto
                        dtm.dbo.next[16+self.config.progbuf_size:16] = debugRegs.abstract_auto_progbuf
                        dtm.dbo.next[self.config.numdata:] = debugRegs.abstract_auto_data
                    elif dtm.adr == 0x20:  # progbuf0
                        dtm.dbo.next = debugRegs.progbuf0
                        # autoexecprogbuf0: complete the register access and
                        # request the last abstract command again.
                        if debugRegs.abstract_auto_progbuf[0] and debugRegs.cmderr == 0:
                            if debugRegs.abstract_command_state != t_abstract_command_state.none:
                                debugRegs.cmderr.next = 1  # busy
                            elif debugRegs.hart_state == t_debug_hart_state.running:
                                debugRegs.cmderr.next = 4
                            else:
                                debugRegs.abstract_command_new.next = True
                    elif self.config.progbuf_size == 2 and dtm.adr == 0x21:  # progbuf1
                        dtm.dbo.next = debugRegs.progbuf1
                        # autoexecprogbuf1 mirrors progbuf0 handling for a
                        # two-entry program buffer.
                        if debugRegs.abstract_auto_progbuf[1] and debugRegs.cmderr == 0:
                            if debugRegs.abstract_command_state != t_abstract_command_state.none:
                                debugRegs.cmderr.next = 1  # busy
                            elif debugRegs.hart_state == t_debug_hart_state.running:
                                debugRegs.cmderr.next = 4
                            else:
                                debugRegs.abstract_command_new.next = True
                    elif (dtm.adr >= 0x04) and (dtm.adr <= 0x04+self.config.numdata-1):  # data0 to dataN
                        data_index = dtm.adr - 0x04
                        dtm.dbo.next = debugRegs.data_regs[data_index]
                        # autoexecdataN returns the current dataN value for this
                        # DMI read and schedules the next abstract command. This
                        # is why repeated data0 reads can stream memory words.
                        if debugRegs.abstract_auto_data[data_index] and debugRegs.cmderr == 0:
                            if debugRegs.abstract_command_state != t_abstract_command_state.none:
                                debugRegs.cmderr.next = 1  # busy
                            elif debugRegs.hart_state == t_debug_hart_state.running:
                                debugRegs.cmderr.next = 4
                            else:
                                debugRegs.abstract_command_new.next = True
                    elif dtm.adr == 0x16:  # abstractcs
                        dtm.dbo.next[29:24] = self.config.progbuf_size  # progbufsize
                        dtm.dbo.next[12] = debugRegs.abstract_command_state != t_abstract_command_state.none  # busy
                        dtm.dbo.next[11:8] = debugRegs.cmderr  # cmderr
                        dtm.dbo.next[4:] = self.config.numdata  # datacount

                else:  # Write
                    if dtm.adr == 0x10:
                        debugRegs.haltreq.next = debugRegs.hart_state == t_debug_hart_state.running and dtm.dbi[31]
                        if debugRegs.hart_state == t_debug_hart_state.halted and dtm.dbi[30]:
                            debugRegs.resumereq.next = True
                            debugRegs.resumeack.next = False

                        debugRegs.hart_reset.next = dtm.dbi[1]  # ndmreset
                    elif (dtm.adr >= 0x04) and (dtm.adr <= 0x04+self.config.numdata-1):  # data0 to dataN
                        data_index = dtm.adr - 0x04
                        debugRegs.data_regs[data_index].next = dtm.dbi
                        # Writes to dataN can also be autoexec triggers. The
                        # written value is visible to the command started here.
                        if debugRegs.abstract_auto_data[data_index] and debugRegs.cmderr == 0:
                            if debugRegs.abstract_command_state != t_abstract_command_state.none:
                                debugRegs.cmderr.next = 1  # busy
                            elif debugRegs.hart_state == t_debug_hart_state.running:
                                debugRegs.cmderr.next = 4
                            else:
                                debugRegs.abstract_command_new.next = True
                    elif dtm.adr == 0x16:  # abstractcs
                        debugRegs.cmderr.next = debugRegs.cmderr & ~dtm.dbi[11:8]  # clear cmderr bits with writing 1 to them
                    elif dtm.adr == 0x18:  # abstractauto
                        # abstractauto[15:0] selects dataN autoexec triggers.
                        # abstractauto[31:16] selects progbufN autoexec triggers.
                        debugRegs.abstract_auto_data.next = dtm.dbi[self.config.numdata:]
                        debugRegs.abstract_auto_progbuf.next = dtm.dbi[16+self.config.progbuf_size:16]
                    elif dtm.adr == 0x17:  # abstract command
                        if debugRegs.cmderr == 0:  # don't start any new command as long as cmderr is not cleared
                            if debugRegs.abstract_command_state != t_abstract_command_state.none:
                                debugRegs.cmderr.next = 1  # busy
                            if debugRegs.hart_state == t_debug_hart_state.running:
                                debugRegs.cmderr.next = 4
                            elif dtm.dbi[32:24] == 0:
                                debugRegs.command_type.next = t_abstract_command_type.access_reg
                                debugRegs.aarsize.next = dtm.dbi[23:20]
                                debugRegs.aarpostincrement.next = dtm.dbi[19]
                                debugRegs.postexec.next = dtm.dbi[18]
                                transfer = dtm.dbi[17]
                                debugRegs.transfer.next = transfer
                                debugRegs.write.next = dtm.dbi[16]
                                debugRegs.regno.next = dtm.dbi[5:0]

                                if dtm.dbi[23:20] == 2 and (dtm.dbi[16:5] == 0x80 or not transfer):  # Only support 32Bit transfers
                                    debugRegs.abstract_command_new.next = True
                                else:
                                    debugRegs.cmderr.next = 2  # not supported
                            # elif dtm.dbi[32:24]==1:
                            #     debugRegs.command_type.next = t_abstract_command_type.quick_access
                            #     debugRegs.abstract_command_state.next=t_abstract_command_state.new
                            else:
                                debugRegs.cmderr.next = 2  # not supported
                    elif dtm.adr == 0x20:  # progbuf0
                        debugRegs.progbuf0.next = dtm.dbi
                        # Allow tools to update progbuf0 and immediately run the
                        # previously configured abstract command.
                        if debugRegs.abstract_auto_progbuf[0] and debugRegs.cmderr == 0:
                            if debugRegs.abstract_command_state != t_abstract_command_state.none:
                                debugRegs.cmderr.next = 1  # busy
                            elif debugRegs.hart_state == t_debug_hart_state.running:
                                debugRegs.cmderr.next = 4
                            else:
                                debugRegs.abstract_command_new.next = True
                    elif self.config.progbuf_size == 2 and dtm.adr == 0x21:
                        debugRegs.progbuf1.next = dtm.dbi
                        # Same autoexec behavior for the optional second
                        # progbuf entry.
                        if debugRegs.abstract_auto_progbuf[1] and debugRegs.cmderr == 0:
                            if debugRegs.abstract_command_state != t_abstract_command_state.none:
                                debugRegs.cmderr.next = 1  # busy
                            elif debugRegs.hart_state == t_debug_hart_state.running:
                                debugRegs.cmderr.next = 4
                            else:
                                debugRegs.abstract_command_new.next = True

        return instances()

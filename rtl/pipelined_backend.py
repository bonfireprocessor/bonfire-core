"""Four- and five-stage Bonfire backend with registered writeback."""

from myhdl import *

from rtl.decode import DecodeBundle
from rtl.execute import ExecuteBundle
from rtl.regfile import RFReadPort, RFWritePort, RegisterFile


class PipelinedBackend:
    def __init__(self, config):
        assert config.pipeline_length in (4, 5)

        self.config = config
        self.reg_portA = RFReadPort(xlen=config.xlen)
        self.reg_portB = RFReadPort(xlen=config.xlen)
        self.reg_writePort = RFWritePort(xlen=config.xlen)

        self.decode = DecodeBundle(config)
        self.execute = ExecuteBundle(config)
        self.issue = DecodeBundle(config) if config.pipeline_length == 5 else None

        if self.issue is not None and config.enableDebugModule:
            # Debug CSR state belongs to the architectural decoder. Execute
            # observes the same bundles through the registered issue view.
            self.issue.debugCSRBundle = self.decode.debugCSRBundle
            self.issue.debugCSRUpdateBundle = self.decode.debugCSRUpdateBundle

    @block
    def backend(self, fetchBundle, frontEnd, databus, clock, reset, out,
                debugport, debugRegisterBundle=None):
        conf = self.config
        with_issue = conf.pipeline_length == 5
        bypass = conf.writeback_bypass

        regfile_inst = RegisterFile(
            clock, self.reg_portA, self.reg_portB,
            self.reg_writePort, conf.xlen)
        decode_inst = self.decode.decoder(
            clock, reset, debugRegisterBundle=debugRegisterBundle)

        execute_input = self.issue if with_issue else self.decode
        exec_inst = self.execute.SimpleExecute(
            execute_input, databus, debugport, clock, reset,
            debugRegisterBundle=debugRegisterBundle)

        if with_issue:
            d_e_inst = self.execute.connect(clock, reset, previous=self.issue)
        else:
            d_e_inst = self.execute.connect(clock, reset, previous=self.decode)
        f_d_inst = self.decode.connect(clock, reset, previous=frontEnd)

        wb_valid = Signal(bool(0))
        wb_we = Signal(bool(0))
        wb_rd = Signal(modbv(0)[5:])
        wb_data = Signal(modbv(0)[conf.xlen:])
        pipeline_pending = Signal(bool(0))

        @always_seq(clock.posedge, reset=reset)
        def writeback_seq():
            wb_valid.next = self.execute.valid_o
            wb_we.next = self.execute.reg_we_o
            wb_rd.next = self.execute.rd_adr_o
            wb_data.next = self.execute.result_o

        @always_comb
        def common_comb():
            self.reg_portA.ra.next = self.decode.rs1_adr_o
            self.reg_portB.ra.next = self.decode.rs2_adr_o

            self.decode.rs1_data_i.next = self.reg_portA.rd
            self.decode.rs2_data_i.next = self.reg_portB.rd

            self.reg_writePort.wa.next = wb_rd
            self.reg_writePort.we.next = wb_valid and wb_we
            self.reg_writePort.wd.next = wb_data

            self.execute.forward_we_i.next = bypass and wb_valid and wb_we
            self.execute.forward_rd_i.next = wb_rd
            self.execute.forward_data_i.next = wb_data

            out.busy_o.next = self.decode.busy_o

            self.decode.word_i.next = fetchBundle.word_i
            self.decode.current_ip_i.next = fetchBundle.current_ip_i
            self.decode.next_ip_i.next = fetchBundle.next_ip_i
            self.decode.fetch_redirect_pending_i.next = fetchBundle.redirect_pending_i
            self.decode.retire_pending_i.next = pipeline_pending

        @always_comb
        def debugout():
            debugport.valid_o.next = wb_valid
            debugport.result_o.next = wb_data
            debugport.rd_adr_o.next = wb_rd
            debugport.reg_we_o.next = wb_valid and wb_we

        if with_issue:
            issue_ready = Signal(bool(0))
            issue_hazard = Signal(bool(0))
            capture_hazard = Signal(bool(0))

            @always_comb
            def issue_control():
                pipeline_pending.next = wb_valid or self.execute.busy_o or \
                    self.issue.valid_o
                hazard_rs1 = wb_valid and wb_we and wb_rd != 0 and \
                    self.issue.valid_o and self.issue.uses_rs1_o and \
                    self.issue.source_rs1_o == wb_rd
                hazard_rs2 = wb_valid and wb_we and wb_rd != 0 and \
                    self.issue.valid_o and self.issue.uses_rs2_o and \
                    self.issue.source_rs2_o == wb_rd
                issue_hazard.next = hazard_rs1 or hazard_rs2

                capture_rs1 = wb_valid and wb_we and wb_rd != 0 and \
                    self.decode.valid_o and self.decode.uses_rs1_o and \
                    self.decode.source_rs1_o == wb_rd
                capture_rs2 = wb_valid and wb_we and wb_rd != 0 and \
                    self.decode.valid_o and self.decode.uses_rs2_o and \
                    self.decode.source_rs2_o == wb_rd
                capture_hazard.next = (capture_rs1 or capture_rs2) and not bypass

                self.execute.hazard_i.next = issue_hazard and not bypass
                issue_ready.next = not self.issue.valid_o or not self.execute.busy_o
                self.decode.stall_i.next = not issue_ready or capture_hazard

                # Execute redirects flush both the architectural decoder and
                # the younger issue entry.
                self.decode.kill_i.next = self.issue.kill_i
                self.decode.execute_ebreak_i.next = self.issue.execute_ebreak_i

            @always_seq(clock.posedge, reset=reset)
            def issue_seq():
                if self.issue.kill_i:
                    self.issue.valid_o.next = False
                elif issue_ready:
                    if capture_hazard:
                        self.issue.valid_o.next = False
                    else:
                        self.issue.valid_o.next = self.decode.valid_o
                        self.issue.op1_o.next = self.decode.op1_o
                        self.issue.op2_o.next = self.decode.op2_o
                        self.issue.rs1_adr_o.next = self.decode.rs1_adr_o
                        self.issue.rs2_adr_o.next = self.decode.rs2_adr_o
                        self.issue.source_rs1_o.next = self.decode.source_rs1_o
                        self.issue.source_rs2_o.next = self.decode.source_rs2_o
                        self.issue.uses_rs1_o.next = self.decode.uses_rs1_o
                        self.issue.uses_rs2_o.next = self.decode.uses_rs2_o
                        self.issue.rd_adr_o.next = self.decode.rd_adr_o
                        self.issue.funct3_onehot_o.next = self.decode.funct3_onehot_o
                        self.issue.funct3_o.next = self.decode.funct3_o
                        self.issue.funct7_o.next = self.decode.funct7_o
                        self.issue.displacement_o.next = self.decode.displacement_o
                        self.issue.jump_dest_o.next = self.decode.jump_dest_o
                        self.issue.next_ip_o.next = self.decode.next_ip_o
                        self.issue.priv_funct_12.next = self.decode.priv_funct_12
                        self.issue.mepc_o.next = self.decode.mepc_o
                        self.issue.alu_cmd.next = self.decode.alu_cmd
                        self.issue.load_cmd.next = self.decode.load_cmd
                        self.issue.store_cmd.next = self.decode.store_cmd
                        self.issue.branch_cmd.next = self.decode.branch_cmd
                        self.issue.jump_cmd.next = self.decode.jump_cmd
                        self.issue.jumpr_cmd.next = self.decode.jumpr_cmd
                        self.issue.csr_cmd.next = self.decode.csr_cmd
                        self.issue.sys_cmd.next = self.decode.sys_cmd
                        self.issue.invalid_opcode.next = self.decode.invalid_opcode
                        self.issue.debug_word_o.next = self.decode.debug_word_o
                        self.issue.debug_current_ip_o.next = self.decode.debug_current_ip_o
                elif issue_hazard and not bypass:
                    # Interlocked instructions stay in Issue for one cycle;
                    # refresh the stale operands from the committing WB entry.
                    if self.issue.uses_rs1_o and self.issue.source_rs1_o == wb_rd:
                        self.issue.op1_o.next = wb_data
                    if self.issue.uses_rs2_o and self.issue.source_rs2_o == wb_rd:
                        self.issue.op2_o.next = wb_data

        else:
            raw_hazard = Signal(bool(0))

            @always_comb
            def four_stage_hazard():
                pipeline_pending.next = wb_valid or self.execute.busy_o
                hazard_rs1 = wb_valid and wb_we and wb_rd != 0 and \
                    self.decode.valid_o and self.decode.uses_rs1_o and \
                    self.decode.source_rs1_o == wb_rd
                hazard_rs2 = wb_valid and wb_we and wb_rd != 0 and \
                    self.decode.valid_o and self.decode.uses_rs2_o and \
                    self.decode.source_rs2_o == wb_rd
                raw_hazard.next = hazard_rs1 or hazard_rs2
                self.execute.hazard_i.next = raw_hazard and not bypass

        if debugRegisterBundle:
            debug_redirect_valid = Signal(bool(0))
            debug_redirect_dest = Signal(modbv(0)[conf.xlen:])

            @always_seq(clock.posedge, reset=reset)
            def debug_redirect_seq():
                debug_redirect_valid.next = debugRegisterBundle.dpc_jump
                debug_redirect_dest.next = concat(
                    debugRegisterBundle.dpc, intbv(0)[conf.ip_low:])

            @always_comb
            def proc_out():
                out.jump_o.next = self.execute.jump_o or debug_redirect_valid
                if debug_redirect_valid:
                    out.jump_dest_o.next = debug_redirect_dest
                else:
                    out.jump_dest_o.next = self.execute.jump_dest_o
        else:
            @always_comb
            def proc_out():
                out.jump_o.next = self.execute.jump_o
                out.jump_dest_o.next = self.execute.jump_dest_o

        return instances()

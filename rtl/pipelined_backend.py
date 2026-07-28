"""Four-stage Bonfire backend with functional-unit result registers.

ALU, load/store, CSR and jump-link values are registered independently. The
writeback result mux therefore sits after those registers while preserving
the architectural four-stage timing.
"""

from myhdl import *

from rtl.decode import DecodeBundle
from rtl.execute import ExecuteBundle
from rtl.regfile import RFReadPort, RFWritePort, RegisterFile


class PipelinedBackend:
    def __init__(self, config):
        assert config.pipeline_length == 4

        self.config = config
        self.reg_portA = RFReadPort(xlen=config.xlen)
        self.reg_portB = RFReadPort(xlen=config.xlen)
        self.reg_writePort = RFWritePort(xlen=config.xlen)

        self.decode = DecodeBundle(config)
        self.execute = ExecuteBundle(config)

    @block
    def backend(self, fetchBundle, frontEnd, databus, clock, reset, out,
                debugport, debugRegisterBundle=None):
        conf = self.config
        bypass = conf.writeback_bypass

        regfile_inst = RegisterFile(
            clock, self.reg_portA, self.reg_portB,
            self.reg_writePort, conf.xlen)
        decode_inst = self.decode.decoder(
            clock, reset, debugRegisterBundle=debugRegisterBundle)

        exec_inst = self.execute.SimpleExecute(
            self.decode, databus, debugport, clock, reset,
            debugRegisterBundle=debugRegisterBundle)
        d_e_inst = self.execute.connect(clock, reset, previous=self.decode)
        f_d_inst = self.decode.connect(clock, reset, previous=frontEnd)

        wb_valid = Signal(bool(0))
        wb_we = Signal(bool(0))
        wb_rd = Signal(modbv(0)[5:])
        wb_alu_valid = Signal(bool(0))
        wb_load_valid = Signal(bool(0))
        wb_csr_valid = Signal(bool(0))
        wb_jump_valid = Signal(bool(0))
        wb_alu_data = Signal(modbv(0)[conf.xlen:])
        wb_load_data = Signal(modbv(0)[conf.xlen:])
        wb_csr_data = Signal(modbv(0)[conf.xlen:])
        wb_jump_data = Signal(modbv(0)[conf.xlen:])
        wb_data = Signal(modbv(0)[conf.xlen:])
        pipeline_pending = Signal(bool(0))

        @always_seq(clock.posedge, reset=reset)
        def writeback_seq():
            wb_valid.next = self.execute.valid_o
            wb_we.next = self.execute.reg_we_o
            wb_rd.next = self.execute.rd_adr_o
            wb_alu_valid.next = self.execute.alu_valid_o
            wb_load_valid.next = self.execute.load_valid_o
            wb_csr_valid.next = self.execute.csr_valid_o
            wb_jump_valid.next = self.execute.jump_valid_o

            wb_alu_data.next = self.execute.alu.res_o
            wb_load_data.next = self.execute.ls.result_o
            wb_csr_data.next = self.execute.csr.result_o
            wb_jump_data.next = self.decode.next_ip_o

        @always_comb
        def writeback_result_mux():
            if wb_alu_valid:
                wb_data.next = wb_alu_data
            elif wb_load_valid:
                wb_data.next = wb_load_data
            elif wb_jump_valid:
                wb_data.next = wb_jump_data
            elif wb_csr_valid:
                wb_data.next = wb_csr_data
            else:
                wb_data.next = 0

        if bypass:
            @always_comb
            def forward_comb():
                self.execute.forward_we_i.next = wb_valid and wb_we
                self.execute.forward_rd_i.next = wb_rd
                self.execute.forward_data_i.next = wb_data
                self.execute.hazard_i.next = False
        else:
            @always_comb
            def four_stage_hazard():
                hazard_rs1 = wb_valid and wb_we and wb_rd != 0 and \
                    self.decode.valid_o and self.decode.uses_rs1_o and \
                    self.decode.source_rs1_o == wb_rd

                hazard_rs2 = wb_valid and wb_we and wb_rd != 0 and \
                    self.decode.valid_o and self.decode.uses_rs2_o and \
                    self.decode.source_rs2_o == wb_rd
                self.execute.hazard_i.next = hazard_rs1 or hazard_rs2

        @always_comb
        def common_comb():
            self.reg_portA.ra.next = self.decode.rs1_adr_o
            self.reg_portB.ra.next = self.decode.rs2_adr_o

            self.decode.rs1_data_i.next = self.reg_portA.rd
            self.decode.rs2_data_i.next = self.reg_portB.rd

            self.reg_writePort.wa.next = wb_rd
            self.reg_writePort.we.next = wb_valid and wb_we
            self.reg_writePort.wd.next = wb_data

            pipeline_pending.next = wb_valid or self.execute.busy_o
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

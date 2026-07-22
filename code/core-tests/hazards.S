// Self-checking RAW hazard test for the four-stage pipeline.
//
// Each producer is immediately followed by its consumer.  With
// writeback_bypass=false Execute must interlock; with it enabled, Execute
// takes the operand from the active writeback entry instead.  Success is a
// write of 1 to monitor@0x10000000; failure writes the expected value to
// monitor+4 and -1 to monitor+0.

.section .text
.global _start
.extern monitor

#define check(_expected) \
  li s2, _expected; \
  jal ra, check_t4

_start:
  la s0, monitor
  addi gp, s0, 0x200       // optional result log area
  la a0, data_area

  // ALU result consumed as both rs1 and rs2.
  addi t0, zero, 7
  add t4, t0, t0
  check(14)

  // ALU result consumed by the pipelined shifter.
  addi t0, zero, 3
  slli t4, t0, 4
  check(48)

  // ALU results consumed as store data and address, respectively.
  addi t0, zero, 0x55
  addi a1, a0, 4
  sw t0, 0(a1)
  lw t4, 0(a1)
  check(0x55)

  // Load result consumed by an ALU operation.
  lw t0, 0(a1)
  addi t4, t0, 1
  check(0x56)

  // Load result consumed as store data.
  lw t0, 0(a1)
  sw t0, 4(a1)
  lw t4, 4(a1)
  check(0x55)

  // ALU result consumed by non-taken and taken branches.
  addi t0, zero, 1
  beq t0, zero, failure
  addi t4, zero, 0x11
  check(0x11)

  addi t0, zero, 1
  bne t0, zero, 1f
  j failure
1:
  addi t4, zero, 0x22
  check(0x22)

  // ALU -> CSR source, CSR result -> ALU, then CSR read -> ALU.
  addi t0, zero, 0x5a
  csrrw t1, mscratch, t0
  addi t4, t1, 1          // mscratch starts at zero
  check(1)

  csrr t0, mscratch
  addi t4, t0, 1
  check(0x5b)

  // JAL and JALR link values consumed immediately by an ALU instruction.
  jal t0, 2f
2:
  addi t4, t0, 0
  la t1, 2b
  bne t4, t1, failure

  la t0, 3f
  jalr t1, t0, 0
3:
  addi t4, t1, 0
  la t2, 3b
  bne t4, t2, failure

  addi t0, zero, 1
  sw t0, 0(s0)

endless:
  j endless

check_t4:
  sw t4, 0(gp)
  addi gp, gp, 4
  beq t4, s2, 4f
  sw s2, 4(s0)
  addi t0, zero, -1
  sw t0, 0(s0)
4:
  ret

failure:
  sw s2, 4(s0)
  addi t0, zero, -1
  sw t0, 0(s0)
  j failure

.align 4
data_area:
  .word 0
  .word 0


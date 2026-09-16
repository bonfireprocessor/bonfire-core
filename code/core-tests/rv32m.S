// Copyright (c) 2026 The Bonfire Project
// License: See LICENSE

// Compact self-checking RV32M integration program.  Success is reported as a
// write of one to monitor@0x10000000; failure writes the expected value at +4
// and -1 at the base address.

.section .text
.global _start
.extern monitor

#define check(_expected) \
  li s2, _expected; \
  jal ra, check_t4

_start:
  la s0, monitor
  addi gp, s0, 0x200

  li t0, 7
  li t1, -3
  mul t4, t0, t1
  check(0xffffffeb)

  li t0, 0x80000000
  li t1, 2
  mulh t4, t0, t1
  check(0xffffffff)

  li t0, -2
  li t1, 0xffffffff
  mulhsu t4, t0, t1
  check(0xfffffffe)

  mulhu t4, t1, t1
  check(0xfffffffe)

  li t0, -17
  li t1, 5
  div t4, t0, t1
  check(-3)
  rem t4, t0, t1
  check(-2)

  li t0, 0xffffffff
  li t1, 16
  divu t4, t0, t1
  check(0x0fffffff)
  remu t4, t0, t1
  check(15)

  // Architectural divide corner cases.
  li t0, 0x80000000
  li t1, -1
  div t4, t0, t1
  check(0x80000000)
  rem t4, t0, t1
  check(0)

  li t0, 0x12345678
  li t1, 0
  divu t4, t0, t1
  check(0xffffffff)
  remu t4, t0, t1
  check(0x12345678)

  // Immediate producer/consumer dependencies and back-to-back M operations.
  li t0, 6
  li t1, 7
  mul t2, t0, t1
  addi t4, t2, 1
  check(43)

  mul t2, t0, t1
  div t3, t2, t0
  addi t4, t3, 0
  check(7)

  // rd=x0 must suppress the architectural write.
  mul zero, t0, t1
  addi t4, zero, 0
  check(0)

  csrr t4, misa
  srli t4, t4, 12
  andi t4, t4, 1
  check(1)

  li t0, 1
  sw t0, 0(s0)

1:
  j 1b

check_t4:
  sw t4, 0(gp)
  addi gp, gp, 4
  beq t4, s2, 2f
  sw s2, 4(s0)
  li t0, -1
  sw t0, 0(s0)
2:
  ret

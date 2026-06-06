.section .text
.global _start
.extern monitor

// Core smoke test for FENCE and FENCE.I.
// PASS criterion: write 1 to monitor base address.
// The instruction encodings are emitted explicitly so the test remains
// independent from toolchains that require zifencei in -march for fence.i.

_start:
  la t0, monitor

  // fence
  .word 0x0000000f
  li t1, 0x11
  sw t1, 4(t0)

  // fence.i
  .word 0x0000100f
  li t1, 0x22
  sw t1, 8(t0)

  li t1, 1
  sw t1, 0(t0)

endless:
  j endless

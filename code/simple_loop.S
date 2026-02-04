.section .text
.global _start
.extern monitor

// Simple self-checking loop test.
// Counts down to zero, then signals success by writing 1 to monitor base.
// On failure, writes -1 to monitor base.

_start:
  li t0, 5

loop:
  addi t0, t0, -1
  bne  t0, x0, loop

  // At this point t0 must be 0
  bne  t0, x0, failure

  la   t1, monitor
  li   t2, 1
  sw   t2, 0(t1)

endless:
  j endless

failure:
  la   t1, monitor
  li   t2, -1
  sw   t2, 0(t1)
  j failure

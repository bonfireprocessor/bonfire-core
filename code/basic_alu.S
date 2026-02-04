.section .text
.global _start
.extern monitor

// Simple self-checking ALU + load/store test.
// Convention: write 1 to monitor base address (0x10000000) on success.
// On mismatch: write expected value to monitor@4, then write -1 to monitor@0.

#define check(_expected) \
  li s2, _expected; \
  jal store

_start:
  la s0, monitor
  add gp, s0, 0x200      // result log area (optional)

  // --- ALU / shift tests ---
  li t0, 10
  li t1, 5

  add t4, t0, t1         // 15
  check(15)

  slli t4, t4, 4         // 240
  check(240)

  ori t4, t4, 5          // 245
  check(245)

  neg t2, t1             // -5
  mv t4, t2
  check(0xfffffffb)

  sltz t4, t2            // (-5 < 0) => 1
  check(1)

  sltiu t4, t2, 0        // unsigned(-5) < 0 => 0
  check(0)

  lui t4, 0x80000        // 0x80000000
  check(0x80000000)

  srai t4, t4, 24        // 0xffffff80
  check(0xffffff80)

  // --- Branch sanity checks (no monitor writes, just self-check) ---
  // beq not taken
  li t4, 0
  beq t0, t2, 1f
  j 2f
1:
  li t4, 1
2:
  check(0)

  // bne taken
  li t4, 0
  bne t0, t2, 3f
  j 4f
3:
  li t4, 1
4:
  check(1)

  // --- Load/store byte test ---
  la a1, data_area
  li t3, 0xdeadbeef
  sw t3, 4(a1)           // bytes at [4..7] = ef be ad de
  lbu t4, 5(a1)          // => 0xbe
  check(0xbe)

  // Success
  li t0, 1
  sw t0, 0(s0)

endless:
  j endless


store:
  // store t4 to mem and increment
  sw t4, 0(gp)           // save result
  add gp, gp, 4          // increment pointer
  beq t4, s2, ok         // check if t4 contains desired result

  sw s2, 4(s0)           // write expected to monitor@4
  li s2, -1
  sw s2, 0(s0)           // write -1 to monitor result address

ok:
  ret


.align 4
data_area:
  .word 0
  .word 0


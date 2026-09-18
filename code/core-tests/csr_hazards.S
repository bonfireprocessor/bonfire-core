// Copyright (c) 2026 The Bonfire Project
// License: See LICENSE

// Self-checking CSR dependency test.
//
// No software bubbles are permitted between a CSR read and its consumer or
// between the MEPC write and MRET.  The two consecutive exceptions also make
// the first handler CSR read observe the trap state just committed by the
// pipeline.  Success writes 1 to monitor@0x10000000, failure writes -1.

.section .text
.global _start
.extern monitor

#include "encoding.h"

_start:
    la      s0, monitor

    // Ordinary CSR write/read and CSR-result/GPR dependencies.
    li      t0, 0x5a5aa5a5
    csrw    mscratch, t0
    csrr    t1, mscratch
    li      s6, 1
    bne     t0, t1, failure

    la      t0, trap_handler
    csrw    mtvec, t0
    csrr    t1, mtvec
    li      s6, 2
    bne     t0, t1, failure

    li      s5, 0

    li      s1, CAUSE_MACHINE_ECALL
    la      s2, ecall_instruction
    la      s3, ebreak_instruction
    li      s6, 0x10
ecall_instruction:
    ecall

    // MRET must use the MEPC value written immediately before it.  The next
    // instruction traps at once, preventing timing gaps from hiding stale
    // trap state.
ebreak_instruction:
    li      s1, CAUSE_BREAKPOINT
    la      s2, breakpoint_instruction
    la      s3, success
    li      s6, 0x20
breakpoint_instruction:
    ebreak

success:
    li      t0, 2
    bne     s5, t0, failure
    li      t0, 1
    sw      t0, 0(s0)
1:
    j       1b

trap_handler:
    csrr    t0, mcause
    bne     t0, s1, failure
    addi    s6, s6, 1
    csrr    t0, mepc
    bne     t0, s2, failure
    addi    s5, s5, 1
    csrw    mepc, s3
    mret

failure:
    sw      s6, 4(s0)
    sw      t0, 8(s0)
    sw      s1, 12(s0)
    li      t0, -1
    sw      t0, 0(s0)
2:
    j       2b

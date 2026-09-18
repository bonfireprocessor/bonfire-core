// Copyright (c) 2026 The Bonfire Project
// License: See LICENSE

// Compact, callable architectural smoke tests used by the SoC monitor.

    .section .text
    .option norvc

    .global monitor_test_m_extension
    .type monitor_test_m_extension, @function
monitor_test_m_extension:
    li      t0, 7
    li      t1, -3
    mul     t2, t0, t1
    li      t3, -21
    bne     t2, t3, .Lm_fail_1

    li      t0, 0x80000000
    li      t1, 2
    mulh    t2, t0, t1
    li      t3, -1
    bne     t2, t3, .Lm_fail_2

    li      t0, -2
    li      t1, -1
    mulhsu  t2, t0, t1
    li      t3, -2
    bne     t2, t3, .Lm_fail_3
    mulhu   t2, t1, t1
    li      t3, -2
    bne     t2, t3, .Lm_fail_4

    li      t0, -17
    li      t1, 5
    div     t2, t0, t1
    li      t3, -3
    bne     t2, t3, .Lm_fail_5
    rem     t2, t0, t1
    li      t3, -2
    bne     t2, t3, .Lm_fail_6

    li      t0, -1
    li      t1, 16
    divu    t2, t0, t1
    li      t3, 0x0fffffff
    bne     t2, t3, .Lm_fail_7
    remu    t2, t0, t1
    li      t3, 15
    bne     t2, t3, .Lm_fail_8

    li      t0, 0x80000000
    li      t1, -1
    div     t2, t0, t1
    bne     t2, t0, .Lm_fail_9
    rem     t2, t0, t1
    bnez    t2, .Lm_fail_10

    li      t0, 0x12345678
    divu    t2, t0, zero
    li      t3, -1
    bne     t2, t3, .Lm_fail_11
    remu    t2, t0, zero
    bne     t2, t0, .Lm_fail_12

    li      t0, 6
    li      t1, 7
    mul     t2, t0, t1
    div     t3, t2, t0
    li      t4, 7
    bne     t3, t4, .Lm_fail_13

    mul     zero, t0, t1
    bnez    zero, .Lm_fail_14

    csrr    t0, misa
    nop
    nop
    srli    t0, t0, 12
    andi    t0, t0, 1
    beqz    t0, .Lm_fail_15

    li      a0, 0
    ret

.Lm_fail_15: li a0, 15; ret
.Lm_fail_14: li a0, 14; ret
.Lm_fail_13: li a0, 13; ret
.Lm_fail_12: li a0, 12; ret
.Lm_fail_11: li a0, 11; ret
.Lm_fail_10: li a0, 10; ret
.Lm_fail_9:  li a0, 9;  ret
.Lm_fail_8:  li a0, 8;  ret
.Lm_fail_7:  li a0, 7;  ret
.Lm_fail_6:  li a0, 6;  ret
.Lm_fail_5:  li a0, 5;  ret
.Lm_fail_4:  li a0, 4;  ret
.Lm_fail_3:  li a0, 3;  ret
.Lm_fail_2:  li a0, 2;  ret
.Lm_fail_1:  li a0, 1;  ret
    .size monitor_test_m_extension, . - monitor_test_m_extension


    .global monitor_test_traps
    .type monitor_test_traps, @function
monitor_test_traps:
    addi    sp, sp, -32
    sw      ra, 28(sp)
    sw      s0, 24(sp)
    sw      s1, 20(sp)
    sw      s2, 16(sp)
    sw      s3, 12(sp)
    sw      s4, 8(sp)
    csrr    t0, mtvec
    sw      t0, 4(sp)
    csrr    t0, mstatus
    sw      t0, 0(sp)

    la      t0, .Ltrap_vector
    csrw    mtvec, t0
    csrsi   mstatus, 8

    // ECALL.
    li      s0, 11
    la      s1, .Ltrap_ecall
    li      s2, 0
    la      s3, .Lafter_ecall
    li      s4, 1
    li      a0, 0
.Ltrap_ecall:
    ecall
.Lafter_ecall:
    bnez    a0, .Ltrap_cleanup

    // EBREAK.
    li      s0, 3
    la      s1, .Ltrap_ebreak
    li      s2, 0
    la      s3, .Lafter_ebreak
    li      s4, 2
.Ltrap_ebreak:
    ebreak
.Lafter_ebreak:
    bnez    a0, .Ltrap_cleanup

    // Illegal opcode.
    li      s0, 2
    la      s1, .Ltrap_illegal
    li      s2, -1
    la      s3, .Lafter_illegal
    li      s4, 3
.Ltrap_illegal:
    .word   0xffffffff
.Lafter_illegal:
    bnez    a0, .Ltrap_cleanup

    // A read-only CSR write is illegal; mtval contains the instruction.
    li      s0, 2
    la      s1, .Ltrap_csr
    li      s2, 0xc0001073
    la      s3, .Lafter_csr
    li      s4, 4
.Ltrap_csr:
    .word   0xc0001073
.Lafter_csr:
    bnez    a0, .Ltrap_cleanup

    // Misaligned word load and store.
    la      t0, .Ltrap_data
    addi    t1, t0, 2
    li      s0, 4
    la      s1, .Ltrap_load_misaligned
    mv      s2, t1
    la      s3, .Lafter_load_misaligned
    li      s4, 5
.Ltrap_load_misaligned:
    lw      t2, 2(t0)
.Lafter_load_misaligned:
    bnez    a0, .Ltrap_cleanup

    la      t0, .Ltrap_data
    addi    t1, t0, 2
    li      s0, 6
    la      s1, .Ltrap_store_misaligned
    mv      s2, t1
    la      s3, .Lafter_store_misaligned
    li      s4, 6
.Ltrap_store_misaligned:
    sw      zero, 2(t0)
.Lafter_store_misaligned:
    bnez    a0, .Ltrap_cleanup

    // JALR clears bit zero, but bit one remains misaligned without RVC.
    la      t0, .Ltrap_aligned_target
    addi    t0, t0, 2
    li      s0, 0
    la      s1, .Ltrap_fetch_misaligned
    mv      s2, t0
    la      s3, .Lafter_fetch_misaligned
    li      s4, 7
.Ltrap_fetch_misaligned:
    jalr    zero, 0(t0)
.Lafter_fetch_misaligned:
    bnez    a0, .Ltrap_cleanup

    // Unmapped SoC addresses are completed with a bus error.
    li      t0, 0x20000000
    li      s0, 5
    la      s1, .Ltrap_load_access
    mv      s2, t0
    la      s3, .Lafter_load_access
    li      s4, 8
.Ltrap_load_access:
    lw      t1, 0(t0)
.Lafter_load_access:
    bnez    a0, .Ltrap_cleanup

    li      s0, 7
    la      s1, .Ltrap_store_access
    mv      s2, t0
    la      s3, .Lafter_store_access
    li      s4, 9
.Ltrap_store_access:
    sw      zero, 0(t0)
.Lafter_store_access:
    j       .Ltrap_cleanup

    .balign 4
.Ltrap_aligned_target:
    li      a0, 10
    j       .Ltrap_cleanup

.Ltrap_vector:
    csrr    t0, mcause
    bne     t0, s0, .Ltrap_fail_cause
    csrr    t0, mepc
    bne     t0, s1, .Ltrap_fail_epc
    csrr    t0, mtval
    bne     t0, s2, .Ltrap_fail_tval
    csrr    t0, mstatus
    andi    t1, t0, 8
    bnez    t1, .Ltrap_fail_mie
    andi    t1, t0, 0x80
    beqz    t1, .Ltrap_fail_mpie
    csrw    mepc, s3
    mret

.Ltrap_fail_mpie:
    li      t1, 5
    j       .Ltrap_fail
.Ltrap_fail_mie:
    li      t1, 4
    j       .Ltrap_fail
.Ltrap_fail_tval:
    li      t1, 3
    j       .Ltrap_fail
.Ltrap_fail_epc:
    li      t1, 2
    j       .Ltrap_fail
.Ltrap_fail_cause:
    li      t1, 1
.Ltrap_fail:
    slli    a0, s4, 3
    add     a0, a0, t1
    csrw    mepc, s3
    mret

.Ltrap_cleanup:
    lw      t0, 4(sp)
    csrw    mtvec, t0
    lw      t0, 0(sp)
    csrw    mstatus, t0
    lw      s4, 8(sp)
    lw      s3, 12(sp)
    lw      s2, 16(sp)
    lw      s1, 20(sp)
    lw      s0, 24(sp)
    lw      ra, 28(sp)
    addi    sp, sp, 32
    ret

    .balign 4
.Ltrap_data:
    .word   0
    .size monitor_test_traps, . - monitor_test_traps

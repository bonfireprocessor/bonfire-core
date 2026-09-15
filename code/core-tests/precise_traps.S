.section .text
.global _start
.extern monitor

#include "encoding.h"

#define TEST_VALUE 0x5a5aa5a5
#define ERROR_ADDRESS 0x20000000

_start:
    la s0, monitor
    la t0, trap_handler
    ori t1, t0, 3
    csrw mtvec, t1
    csrr t1, mtvec
    nop
    nop
    bne t0, t1, test_failure

    li s5, 0
    li s7, 0

    # ECALL also verifies MIE/MPIE entry and MRET restoration.
    csrsi mstatus, MSTATUS_MIE
    li s1, CAUSE_MACHINE_ECALL
    la s2, ecall_instruction
    li s3, 0
    la s4, after_ecall
ecall_instruction:
    ecall
after_ecall:
    csrr t0, mstatus
    nop
    nop
    andi t0, t0, MSTATUS_MIE
    beqz t0, test_failure

    li s1, CAUSE_BREAKPOINT
    la s2, ebreak_instruction
    li s3, 0
    la s4, after_ebreak
ebreak_instruction:
    ebreak
after_ebreak:

    li t6, TEST_VALUE
    li s1, CAUSE_ILLEGAL_INSTRUCTION
    la s2, illegal_instruction
    li s3, -1
    la s4, after_illegal
    li s7, 1
    csrr s6, minstret
illegal_instruction:
    .word 0xffffffff
after_illegal:
    li s7, 0
    li t0, TEST_VALUE
    bne t6, t0, test_failure

    li t6, TEST_VALUE
    li s1, CAUSE_ILLEGAL_INSTRUCTION
    la s2, illegal_csr_instruction
    la s3, illegal_csr_instruction
    lw s3, 0(s3)
    la s4, after_illegal_csr
illegal_csr_instruction:
    csrrw t6, cycle, zero
after_illegal_csr:
    li t0, TEST_VALUE
    bne t6, t0, test_failure

    la a0, data_area
    li t6, TEST_VALUE
    li s1, CAUSE_MISALIGNED_LOAD
    la s2, misaligned_load_instruction
    addi s3, a0, 2
    la s4, after_misaligned_load
misaligned_load_instruction:
    lw t6, 2(a0)
after_misaligned_load:
    li t0, TEST_VALUE
    bne t6, t0, test_failure

    li t0, TEST_VALUE
    sw t0, 0(a0)
    li s1, CAUSE_MISALIGNED_STORE
    la s2, misaligned_store_instruction
    addi s3, a0, 2
    la s4, after_misaligned_store
misaligned_store_instruction:
    sw zero, 2(a0)
after_misaligned_store:
    lw t1, 0(a0)
    li t0, TEST_VALUE
    bne t1, t0, test_failure

    li t6, TEST_VALUE
    la t0, aligned_jump_target
    addi t0, t0, 2
    li s1, CAUSE_MISALIGNED_FETCH
    la s2, misaligned_jump_instruction
    addi s3, t0, 0
    la s4, after_misaligned_jump
misaligned_jump_instruction:
    jalr t6, 0(t0)
after_misaligned_jump:
    li t1, TEST_VALUE
    bne t6, t1, test_failure

    li t6, TEST_VALUE
    li t0, ERROR_ADDRESS
    li s1, CAUSE_FAULT_LOAD
    la s2, load_access_fault_instruction
    li s3, ERROR_ADDRESS
    la s4, after_load_access_fault
load_access_fault_instruction:
    lw t6, 0(t0)
after_load_access_fault:
    li t1, TEST_VALUE
    bne t6, t1, test_failure

    li t0, ERROR_ADDRESS
    li s1, CAUSE_FAULT_STORE
    la s2, store_access_fault_instruction
    li s3, ERROR_ADDRESS
    la s4, after_store_access_fault
store_access_fault_instruction:
    sw zero, 0(t0)
after_store_access_fault:

    li t0, 9
    bne s5, t0, test_failure
    li t0, 1
    sw t0, 0(s0)

halt:
    j halt

trap_handler:
    csrr t0, mcause
    nop
    nop
    bne t0, s1, test_failure
    csrr t0, mepc
    nop
    nop
    bne t0, s2, test_failure
    csrr t0, mtval
    nop
    nop
    bne t0, s3, test_failure

    csrr t0, mstatus
    nop
    nop
    andi t1, t0, MSTATUS_MIE
    bnez t1, test_failure
    andi t1, t0, MSTATUS_MPIE
    beqz t1, test_failure

    beqz s7, retirement_check_done
    csrr t0, minstret
    nop
    nop
    # The baseline CSR read and twenty preceding handler instructions retire;
    # the faulting instruction itself must not add another retirement.
    addi t1, s6, 21
    bne t0, t1, test_failure
retirement_check_done:
    addi s5, s5, 1
    csrw mepc, s4
    mret

aligned_jump_target:
    j test_failure

test_failure:
    li t0, -1
    sw t0, 0(s0)
    j halt

.align 4
data_area:
    .word 0

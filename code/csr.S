.section .text
.global _start
.extern monitor

#include "encoding.h"

#define check(_result) \
  li s2,_result; \
  jal store \

#define check_csr(_csr,_result) \
    csrr t4,_csr; \
    li s2,_result; \
    jal store \



_start:



la s0, monitor
add gp,s0,0x200 // test result area

la s2, trap_failure 
csrw mtvec,s2

csrr t4,mtvec
jal store // same as check macrp because s2 contains the comparison value

li t1, 0xdeadbeef
csrw mscratch,t1
check_csr(mscratch,0xdeadbeef)


check_csr(mimpid,0x8000)
check_csr(misa,0x40000000)
check_csr(mvendorid,0)
check_csr(marchid,0)
check_csr(mhartid,0)


check_csr(mstatus,0x1800)

csrsi mstatus,MSTATUS_MIE
check_csr(mstatus,0x1808)

csrci mstatus, MSTATUS_MIE
check_csr(mstatus,0x1800)

li t4,MSTATUS_MPIE
csrs mstatus,t4
check(MSTATUS_MPIE) // Check if csrs instruction globbers rs register
check_csr(mstatus,0x1880)

li t1,MSTATUS_MPIE 
csrc mstatus,t1
check_csr(mstatus,0x1800)

li t1,0xdead0000
csrw mepc,t1
check_csr(mepc,0xdead0000)


// // Read mcycle/h and write to monitor
// csrr t1,mcycle
// sw t1,24(s0)
// beqz t1, finish // failure->
// csrr t1,mcycleh
// sw t1,28(s0)

// csrr t1,minstret
// sw t1,32(s0)
// beqz t1, finish // failure->
// csrr t1,minstreth
// sw t1,36(s0)


// // Test mstatus register
// csrr t1,mstatus
// sw t1,20(s0) // write to monitor
// li t2,0x8 // set MIE bit
// csrs mstatus,t2
// csrr t1,mstatus
// sw t1,20(s0) // write to monitor


// // Test IE Bit
// la t1,trap_mstatus
// csrw mtvec,t1
// ecall
// csrr t1,mstatus
// sw t1,20(s0) // write to monitor
// andi t1,t1,0x08  // mask MIE
// beqz t1, finish // failure when MIE is not set


li a0,1 // success
j finish

trap_failure: // should not be called
csrr t1,mepc
sw t1,12(s0)
csrr t1,mcause
sw t1,16(s0)
/// fall through finish/failure

finish:
sw a0,0(s0) // write  to monitor result register
f0:
j f0

trap_mstatus:
csrr t1,mepc
sw t1,12(s0)
csrr t1, mstatus
sw t1,20(s0)
andi t1,t1, 0x088 // mask MPIE and MIE
addi t1,t1,-0x80   // result should be 80
bnez t1,finish  // failure.. if not 80
csrr t1,mepc
addi t1,t1,4
csrw mepc,t1
mret


store: // store t4 to mem and increment
sw t4,0(gp) // save result
add gp,gp,4 // increment pointer
beq t4,s2,ok // check if t4 contains desired result

sw s2,4(s0) // write check value to monitor@4 
li s2,-1
sw s2,(s0)  // write -1 to monitor result address

ok:
ret

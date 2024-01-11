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

#define check_csra(_csr,_result) \
    csrr t4,_csr; \
    la s2,_result; \
    jal store \


_start:

la s0, monitor
add gp,s0,0x200 // test result area

la s2, trap_mstatus
csrw mtvec,s2


ecalladr: // Required to verify mepc
ecall
// When we come to this point we are ok
finish:
sw a0,0(s0) // write  to monitor result register
f0:
j f0


trap_mstatus:

check_csra(mepc,ecalladr)
check_csr(mcause,0xb)

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
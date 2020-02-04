.section .text
.global _start
.extern monitor
_start:

li a0,10 // loop counter
la s0, monitor
li a1,0x5588 // signature

loop:
addi a0,a0,-1
sw a0,4(s0)
bnez a0, loop
sw a1,4(s0) // write signature to verify execution of this statement

// Forward branch test
li a0, -1
bnez a0, forward
sw a0,0(s0) // should not happen...
forward:
// jalr test and call return test
la s1, subroutine
jalr ra, s1
sw a0,4(s0) // should write #55aaffee


j double

success:
li a0,1
sw a0,0(s0) // write success to monitor result register
f0:
j f0

subroutine:
li a0, 0x55aaffee
ret

fail:
li a0, -1
sw a0,0(s0) // should not happen...

// Double branch tests
double:
bne a0,a0, fail
beq a0,a0, success

j fail

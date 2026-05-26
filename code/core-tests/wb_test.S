.section .text
.global _start
.extern monitor
.extern wb_base

_start:
la a2, wb_base
li t1, 0xdeadbeef
la a3, monitor 
li a1, 10

loop:
addi a1, a1, -1

sw a1,0(a2)
lw t2,0(a2) // bfm will always return 0xdeadbeef

bne t2,t1, error
bne a1,x0, loop 
li a1,1 // success 
sw a1,0(a3)

error:
li a1,-1
sw a1, 0(a3)

j error // should not happen....

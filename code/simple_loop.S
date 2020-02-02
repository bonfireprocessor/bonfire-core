.section .text
.global _start
.extern monitor

_start:
li a1, 5
loop:
addi a1, a1, -1
bne a1,x0, loop 

la a2, monitor 
sw a1, 0(a2)
j _start // should not happen....

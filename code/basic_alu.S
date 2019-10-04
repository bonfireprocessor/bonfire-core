.section .text
.global _start
_start:

li a1,10 
li a2,5
add a3,a1,a2
slli a3,a3,4
ori a3,a3,5
beq a1,a2, _start 

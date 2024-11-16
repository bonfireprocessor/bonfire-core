// Code for debug module unit test

.section .text
.global _start
.extern monitor
_start:

li a1,0xdeadbeef // signature
li a0,0 // Debugger test will set this to 1 
endless:
j endless // Debugger test will bring us out of here 

success:
la s0, monitor 

sw a0,0(s0) // write success to monitor result register
f0:
j f0


.section .text
.global _start
_start:

// Endless Loop waiting forever
// intended for use with the gdbserver
li a0,0
li a1,0xdeadbeef // Just for testing the debugger interface
loop:
add a0,a0,1
j loop

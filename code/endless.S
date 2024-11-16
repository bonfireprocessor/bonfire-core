.section .text
.global _start
_start:

// Endless Loop waiting forever
// intended for use with the gdbserver
la t0, counter
li t1,0xdeadbeef // Just for testing the debugger interface
loop:
lw t2, (t0)
add t2,t2,1
sw t2, (t0)
j loop

counter: .long 0
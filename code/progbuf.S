// Collection of Statements for Progbuf access. Not intented to be run
// See Examples in RISC-V Debug Spec

.section .text
.global _start
.extern monitor
_start:

// For memory read
lw s0,0(s0)

// For memory write
sw s1,0(s0)
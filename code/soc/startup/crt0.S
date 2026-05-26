.section .init, "ax"
.global _start

_start:
    la sp, _stacktop

    la t0, _fbss
    la t1, _ebss
    beq t0, t1, 2f

1:
    sw zero, 0(t0)
    addi t0, t0, 4
    bltu t0, t1, 1b

2:
    call main

3:
    j 3b

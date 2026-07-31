.section .init, "ax"
.global _start
.type _start, @function

_start:
    .option push
    .option norelax
    la gp, __global_pointer$
    .option pop

    la sp, _stacktop

    /* Copy initialized data when its load and run addresses differ. */
    la t0, __data_source
    la t1, __data_start
    la t2, __data_end
    beq t0, t1, 2f

1:
    beq t1, t2, 2f
    lw t3, 0(t0)
    sw t3, 0(t1)
    addi t0, t0, 4
    addi t1, t1, 4
    j 1b

2:
    la t0, __bss_start
    la t1, __bss_end
    beq t0, t1, 4f

3:
    sw zero, 0(t0)
    addi t0, t0, 4
    bltu t0, t1, 3b

4:
    call __libc_init_array
    call main

5:
    j 5b

.size _start, . - _start

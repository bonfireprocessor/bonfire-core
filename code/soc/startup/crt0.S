.section .init, "ax"
.global _start

_start:
    la sp, _stacktop
    call main

1:
    j 1b

ENTRY(_start)

SECTIONS
{
    . = ORIGIN(RAM);
    _rombase = .;

    .text : ALIGN(4)
    {
        KEEP(*(.init))
        *(.text .text.*)
    } > RAM

    .rodata : ALIGN(4)
    {
        *(.rdata)
        *(.rodata .rodata.*)
    } > RAM

    .data : ALIGN(4)
    {
        *(.data .data.*)
        *(.sdata .sdata.*)
        _edata = .;
    } > RAM

    .bss (NOLOAD) : ALIGN(4)
    {
        _fbss = .;
        *(.sbss .sbss.*)
        *(.bss .bss.*)
        *(COMMON)
        . = ALIGN(4);
        _ebss = .;
        end = .;
        _end = .;
        __end = .;
    } > RAM

    _stacktop = ALIGN(16, ORIGIN(RAM) + LENGTH(RAM)) - 16;
}

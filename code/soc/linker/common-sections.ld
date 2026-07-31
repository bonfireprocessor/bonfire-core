ENTRY(_start)

SECTIONS
{
    . = ORIGIN(RAM);
    _rombase = .;

    .text : ALIGN(4)
    {
        KEEP(*(.init))
        *(.text .text.*)
        KEEP(*(.fini))
    } > RAM

    .rodata : ALIGN(4)
    {
        *(.rdata)
        *(.rodata .rodata.*)
        *(.srodata .srodata.*)
    } > RAM

    .preinit_array : ALIGN(4)
    {
        PROVIDE_HIDDEN(__preinit_array_start = .);
        KEEP(*(.preinit_array))
        PROVIDE_HIDDEN(__preinit_array_end = .);
    } > RAM

    .init_array : ALIGN(4)
    {
        PROVIDE_HIDDEN(__init_array_start = .);
        KEEP(*(SORT_BY_INIT_PRIORITY(.init_array.*)))
        KEEP(*(.init_array))
        PROVIDE_HIDDEN(__init_array_end = .);
    } > RAM

    .fini_array : ALIGN(4)
    {
        PROVIDE_HIDDEN(__fini_array_start = .);
        KEEP(*(SORT_BY_INIT_PRIORITY(.fini_array.*)))
        KEEP(*(.fini_array))
        PROVIDE_HIDDEN(__fini_array_end = .);
    } > RAM

    .data : ALIGN(4)
    {
        __data_start = .;
        PROVIDE(__global_pointer$ = . + 0x800);
        *(.data .data.*)
        *(.sdata .sdata.*)
        . = ALIGN(4);
        __data_end = .;
        _edata = .;
    } > RAM
    __data_source = LOADADDR(.data);
    __data_size = SIZEOF(.data);

    .bss (NOLOAD) : ALIGN(4)
    {
        __bss_start = .;
        _fbss = .;
        *(.sbss .sbss.*)
        *(.bss .bss.*)
        *(COMMON)
        . = ALIGN(4);
        __bss_end = .;
        _ebss = .;
        end = .;
        _end = .;
        __end = .;
    } > RAM

    _stacktop = ALIGN(16, ORIGIN(RAM) + LENGTH(RAM)) - 16;
    ASSERT(_end <= _stacktop, "RAM overflow: sections overlap the stack")
}

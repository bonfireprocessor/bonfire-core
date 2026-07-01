MEMORY
{
    RAM (rwx) : ORIGIN = 0x00000000, LENGTH = 0x00010000
}

ENTRY(_start)

SECTIONS
{
    . = 0x0;
    .text :
    {
        KEEP(*(.text.start))
        *(.text)
    } > RAM

    .data : { *(.data) } > RAM
    .bss :
    {
        *(.bss)
        *(COMMON)
    } > RAM
}

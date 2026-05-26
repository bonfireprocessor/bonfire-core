#include <stdarg.h>

#include <bonfire/console.h>
#include <bonfire/uart.h>

static void vprintk(const char *format, va_list args)
{
    static char out[256];

    vsnprintf(out, sizeof(out), format, args);
    bonfire_uart_puts(out);
}

void printk(const char *format, ...)
{
    va_list args;

    va_start(args, format);
    vprintk(format, args);
    va_end(args);
}

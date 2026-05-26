#ifndef BONFIRE_CONSOLE_H
#define BONFIRE_CONSOLE_H

#include <stdarg.h>
#include <stddef.h>

int vsnprintf(char *out, size_t n, const char *format, va_list args);
int snprintf(char *out, size_t n, const char *format, ...);
void printk(const char *format, ...);

#endif

#include <stdbool.h>
#include <stdarg.h>
#include <stddef.h>
#include <stdint.h>

#include <bonfire/console.h>

static void put_char(char *out, size_t n, size_t *pos, char c)
{
    if (++(*pos) < n) {
        out[*pos - 1u] = c;
    }
}

static void put_string(char *out, size_t n, size_t *pos, const char *value)
{
    while (*value != '\0') {
        put_char(out, n, pos, *value++);
    }
}

static unsigned long divmod10(unsigned long value, unsigned long *remainder)
{
    unsigned long quotient = 0;
    unsigned long current = 1;
    unsigned long denom = 10;

    while ((denom << 1) > denom && (denom << 1) <= value) {
        denom <<= 1;
        current <<= 1;
    }

    while (current != 0u) {
        if (value >= denom) {
            value -= denom;
            quotient |= current;
        }
        denom >>= 1;
        current >>= 1;
    }

    *remainder = value;
    return quotient;
}

static void put_unsigned(char *out, size_t n, size_t *pos, unsigned long value,
                         unsigned int base, bool prefix_hex, bool longarg)
{
    static const char digits[] = "0123456789abcdef";
    char buffer[3u * sizeof(unsigned long)];
    int width = 0;

    if (prefix_hex) {
        put_string(out, n, pos, "0x");
    }

    if (base == 16u) {
        width = 2 * (longarg ? (int)sizeof(unsigned long) : (int)sizeof(unsigned int));
        for (int i = width - 1; i >= 0; i--) {
            put_char(out, n, pos, digits[(value >> (4 * i)) & 0x0fu]);
        }
        return;
    }

    do {
        unsigned long remainder;

        (void)base;
        value = divmod10(value, &remainder);
        buffer[width++] = digits[remainder];
    } while (value != 0u);

    while (width > 0) {
        put_char(out, n, pos, buffer[--width]);
    }
}

int vsnprintf(char *out, size_t n, const char *format, va_list args)
{
    bool in_format = false;
    bool longarg = false;
    size_t pos = 0;

    for (; *format != '\0'; format++) {
        if (!in_format) {
            if (*format == '%') {
                in_format = true;
            } else {
                put_char(out, n, &pos, *format);
            }
            continue;
        }

        switch (*format) {
        case 'l':
            longarg = true;
            break;
        case 'p':
            longarg = true;
            put_unsigned(out, n, &pos, (uintptr_t)va_arg(args, void *), 16u, true, longarg);
            in_format = false;
            longarg = false;
            break;
        case 'x':
            put_unsigned(out, n, &pos,
                         longarg ? va_arg(args, unsigned long) : va_arg(args, unsigned int),
                         16u, false, longarg);
            in_format = false;
            longarg = false;
            break;
        case 'u':
            put_unsigned(out, n, &pos,
                         longarg ? va_arg(args, unsigned long) : va_arg(args, unsigned int),
                         10u, false, longarg);
            in_format = false;
            longarg = false;
            break;
        case 'd':
        {
            long value = longarg ? va_arg(args, long) : va_arg(args, int);

            if (value < 0) {
                put_char(out, n, &pos, '-');
                value = -value;
            }
            put_unsigned(out, n, &pos, (unsigned long)value, 10u, false, longarg);
            in_format = false;
            longarg = false;
            break;
        }
        case 's':
            put_string(out, n, &pos, va_arg(args, const char *));
            in_format = false;
            longarg = false;
            break;
        case 'c':
            put_char(out, n, &pos, (char)va_arg(args, int));
            in_format = false;
            longarg = false;
            break;
        case '%':
            put_char(out, n, &pos, '%');
            in_format = false;
            longarg = false;
            break;
        default:
            in_format = false;
            longarg = false;
            break;
        }
    }

    if (pos < n) {
        out[pos] = '\0';
    } else if (n != 0u) {
        out[n - 1u] = '\0';
    }

    return (int)pos;
}

int snprintf(char *out, size_t n, const char *format, ...)
{
    va_list args;
    int result;

    va_start(args, format);
    result = vsnprintf(out, n, format, args);
    va_end(args);

    return result;
}

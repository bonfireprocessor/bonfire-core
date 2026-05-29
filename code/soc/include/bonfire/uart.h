#ifndef BONFIRE_UART_H
#define BONFIRE_UART_H

#include <stdint.h>

#include <bonfire/mmio.h>
#include <bonfire/platform.h>

#define BONFIRE_UART_TX 0x00u
#define BONFIRE_UART_STATUS 0x04u
#define BONFIRE_UART_CONTROL 0x08u

#define BONFIRE_UART_STATUS_RX_READY 0x01u
#define BONFIRE_UART_STATUS_TX_READY 0x02u
#define BONFIRE_UART_STATUS_TX_ACTIVE 0x04u
#define BONFIRE_UART_CONTROL_ENABLE_EXTENDED 0x030000u
#define BONFIRE_UART_CONTROL_DIVISOR_MASK 0x0000ffffu
#define BONFIRE_UART_CONTROL_VERIFY_MASK 0x0003ffffu

#if defined(BONFIRE_PLATFORM_ICEPIZERO)
static inline void wait(long nWait)
{
    static volatile int c;

    c = 0;
    while (c++ < nWait) {}
}
#endif

static inline uint32_t bonfire_uart_divisor(void)
{
    return (BONFIRE_SYSCLK_HZ / BONFIRE_UART_BAUD) - 1u;
}

static inline uint32_t bonfire_uart_control_value(uint32_t divisor)
{
    return BONFIRE_UART_CONTROL_ENABLE_EXTENDED | (divisor & BONFIRE_UART_CONTROL_DIVISOR_MASK);
}

static inline void bonfire_uart_init(uint32_t divisor)
{
    bonfire_write32(BONFIRE_UART0_BASE + BONFIRE_UART_CONTROL,
                    bonfire_uart_control_value(divisor));
}

static inline uint32_t bonfire_uart_read_control(void)
{
    return bonfire_read32(BONFIRE_UART0_BASE + BONFIRE_UART_CONTROL);
}

static inline void bonfire_uart_wait_tx_ready(void)
{
    while ((bonfire_read32(BONFIRE_UART0_BASE + BONFIRE_UART_STATUS) & BONFIRE_UART_STATUS_TX_READY) == 0u) {}
}

static inline void bonfire_uart_putc(char c)
{
    bonfire_uart_wait_tx_ready();
    bonfire_write32(BONFIRE_UART0_BASE + BONFIRE_UART_TX, (uint32_t)c);
    // #if defined(BONFIRE_PLATFORM_ICEPIZERO)
    //    #pragma message "Implementing delay"
    //    wait(1000);
    // #endif
}

static inline void bonfire_uart_puts(const char *text)
{
    while (*text != '\0') {
        if (*text == '\n') {
            bonfire_uart_putc('\r');
        }
        bonfire_uart_putc(*text++);
    }
}

static inline void bonfire_uart_wait_tx_complete(void)
{
    uint32_t status;

    do {
        status = bonfire_read32(BONFIRE_UART0_BASE + BONFIRE_UART_STATUS);
    } while ((status & BONFIRE_UART_STATUS_TX_ACTIVE) == 0u);

    do {
        status = bonfire_read32(BONFIRE_UART0_BASE + BONFIRE_UART_STATUS);
    } while ((status & (BONFIRE_UART_STATUS_TX_READY | BONFIRE_UART_STATUS_TX_ACTIVE)) != BONFIRE_UART_STATUS_TX_READY);
}

#endif

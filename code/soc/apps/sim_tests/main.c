// Copyright (c) 2026 The Bonfire Project
// License: See LICENSE

/* Fast, self-checking firmware for RTL simulation. */

#include <stdint.h>

#include <bonfire/uart.h>

extern uint32_t monitor_test_m_extension(void);
extern uint32_t monitor_test_traps(void);

#define SIM_PASS_MARKER 0x1au
#define SIM_FAIL_MARKER 0x1bu

static void put_hex_byte(uint32_t value)
{
    static const char digits[] = "0123456789abcdef";

    bonfire_uart_putc(digits[(value >> 4) & 0xfu]);
    bonfire_uart_putc(digits[value & 0xfu]);
}

static void finish_success(void)
{
    bonfire_uart_putc(SIM_PASS_MARKER);
    bonfire_uart_wait_tx_complete();
    for (;;) {}
}

static void finish_failure(const char *name, uint32_t group, uint32_t code)
{
    bonfire_uart_puts(name);
    bonfire_uart_puts(": FAIL:");
    put_hex_byte(group);
    put_hex_byte(code);
    bonfire_uart_putc('\n');
    bonfire_uart_putc(SIM_FAIL_MARKER);
    bonfire_uart_wait_tx_complete();
    for (;;) {}
}

int main(void)
{
    uint32_t failure;

    bonfire_uart_init(bonfire_uart_divisor());

    failure = monitor_test_m_extension();
    if (failure != 0u) {
        finish_failure("M Test", 1u, failure);
    }
    bonfire_uart_puts("M Test: OK\n");

    failure = monitor_test_traps();
    if (failure != 0u) {
        finish_failure("Trap Test", 2u, failure);
    }
    bonfire_uart_puts("Trap Test: OK\n");

    finish_success();
}

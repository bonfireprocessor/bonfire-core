#include <stdint.h>

#include <bonfire/mmio.h>
#include <bonfire/platform.h>
#include <bonfire/uart.h>

static char uart_getc(void)
{
    while ((bonfire_read32(BONFIRE_UART0_BASE + BONFIRE_UART_STATUS)
            & BONFIRE_UART_STATUS_RX_READY) == 0u) {}

    return (char)bonfire_read32(BONFIRE_UART0_BASE + BONFIRE_UART_RX);
}

int main(void)
{
    static const char message[] = "Hello";
    uint32_t index;

    /* A short bit period keeps RTL integration tests fast. */
    bonfire_uart_init(7u);

    for (index = 0; message[index] != '\0'; ++index) {
        bonfire_uart_putc(message[index]);
        if (uart_getc() != message[index]) {
            bonfire_write32(BONFIRE_LED_BASE, 0u);
            for (;;) {}
        }
    }

    bonfire_uart_putc(0x1a);
    bonfire_uart_wait_tx_complete();
    bonfire_write32(BONFIRE_LED_BASE, BONFIRE_LED_MASK);

    for (;;) {}
}

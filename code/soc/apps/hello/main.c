#include <stdint.h>

#include <bonfire/console.h>
#include <bonfire/gpio.h>
#include <bonfire/mmio.h>
#include <bonfire/platform.h>
#include <bonfire/uart.h>

static void led_out(uint32_t value)
{
    bonfire_write32(BONFIRE_LED_BASE, value & BONFIRE_LED_MASK);
}

#if BONFIRE_ENABLE_GPIO
static void gpio_write(uint32_t value)
{
    bonfire_write32(BONFIRE_GPIO_BASE + BONFIRE_GPIO_OUTPUT_EN, 0xff);
    bonfire_write32(BONFIRE_GPIO_BASE + BONFIRE_GPIO_OUTPUT_VAL, value);
}
#endif

static void report_platform(void)
{
    printk("\nHello from Bonfire Core!\n");
    printk("platform=%s\n", BONFIRE_PLATFORM_NAME);
    printk("sysclk=%u\n", BONFIRE_SYSCLK_HZ);
    printk("baud=%u\n", BONFIRE_UART_BAUD);
    printk("sram_base=0x%x\n\n", BONFIRE_SRAM_BASE); // Two new lines for smoother VHDL test output in case of sim.
}

int main(void)
{
    uint32_t uart_divisor = bonfire_uart_divisor();
    uint32_t uart_control = bonfire_uart_control_value(uart_divisor);
    uint32_t uart_control_readback;

    led_out(1u);
    bonfire_uart_init(uart_divisor);
    uart_control_readback = bonfire_uart_read_control();
    led_out(2u);
    if ((uart_control_readback & BONFIRE_UART_CONTROL_VERIFY_MASK) != uart_control) {
        led_out(BONFIRE_LED_MASK);
        while (1) {}
    }
    led_out(3u);
    report_platform();

#if BONFIRE_ENABLE_GPIO
    uint32_t i = 0;

    while (i < 8) {
        uint32_t value = 1u << i;

        gpio_write(value);
        i++;      
    }
#endif
    led_out(4u);
#if defined(BONFIRE_PLATFORM_SIM)
    bonfire_uart_putc(0x1a);
    bonfire_uart_wait_tx_complete();
#endif

    uint32_t counter = 0;

    while (1) {
        bonfire_write32(BONFIRE_LED_BASE, (counter++) & BONFIRE_LED_MASK);
        report_platform();
    }    
}

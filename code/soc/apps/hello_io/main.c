#include <stdint.h>

#include <bonfire/console.h>
#include <bonfire/gpio.h>
#include <bonfire/mmio.h>
#include <bonfire/platform.h>
#include <bonfire/spi.h>
#include <bonfire/uart.h>

#define GPIO_TEST_MASK 0xffu
#define GPIO_TIMEOUT_READS 64u

static void led_out(uint32_t value)
{
    bonfire_write32(BONFIRE_LED_BASE, value & BONFIRE_LED_MASK);
}

static void finish_test(uint32_t led_value)
{
    led_out(led_value);
    bonfire_uart_putc(0x1a);
    bonfire_uart_wait_tx_complete();

    for (;;) {}
}

static void report_platform(void)
{
    printk("\nHello from Bonfire Core!\n");
    printk("platform=%s\n", BONFIRE_PLATFORM_NAME);
    printk("sysclk=%u\n", BONFIRE_SYSCLK_HZ);
    printk("baud=%u\n", BONFIRE_UART_BAUD);
    printk("sram_base=0x%x\n\n", BONFIRE_SRAM_BASE);
}

static int gpio_wait_for_value(uint32_t expected)
{
    uint32_t timeout;

    for (timeout = 0; timeout < GPIO_TIMEOUT_READS; ++timeout) {
        uint32_t value = bonfire_read32(
            BONFIRE_GPIO_BASE + BONFIRE_GPIO_INPUT_VAL) & GPIO_TEST_MASK;
        if (value == expected) {
            return 1;
        }
    }

    return 0;
}

static int test_gpio(void)
{
    static const uint8_t patterns[] = {
        0x00u, 0x01u, 0x02u, 0x04u, 0x08u, 0x10u,
        0x20u, 0x40u, 0x80u, 0x55u, 0xaau, 0xffu,
    };
    uint32_t index;

    printk("GPIO test: start\n");
    bonfire_write32(BONFIRE_GPIO_BASE + BONFIRE_GPIO_OUTPUT_VAL, 0u);
    bonfire_write32(BONFIRE_GPIO_BASE + BONFIRE_GPIO_INPUT_EN, GPIO_TEST_MASK);
    bonfire_write32(BONFIRE_GPIO_BASE + BONFIRE_GPIO_OUTPUT_EN, GPIO_TEST_MASK);

    for (index = 0; index < sizeof(patterns); ++index) {
        uint32_t expected = patterns[index];

        bonfire_write32(BONFIRE_GPIO_BASE + BONFIRE_GPIO_OUTPUT_VAL, expected);
        if (!gpio_wait_for_value(expected)) {
            printk("GPIO test: FAIL pattern=0x%x read=0x%x\n", expected,
                   bonfire_read32(BONFIRE_GPIO_BASE + BONFIRE_GPIO_INPUT_VAL)
                       & GPIO_TEST_MASK);
            return 0;
        }
    }

    printk("GPIO test: OK\n");
    return 1;
}

static int test_spi_loopback(void)
{
    static const uint8_t patterns[] = {0x00u, 0x55u, 0xa5u, 0xffu};
    uint32_t index;

    printk("SPI loopback test: start\n");
    bonfire_write32(BONFIRE_SPI_FLASH_BASE + BONFIRE_SPI_CLOCK, 1u);
    bonfire_write32(BONFIRE_SPI_FLASH_BASE + BONFIRE_SPI_CONTROL,
                    BONFIRE_SPI_CONTROL_AUTOWAIT);

    for (index = 0; index < sizeof(patterns); ++index) {
        uint32_t expected = patterns[index];
        uint32_t received;

        bonfire_write32(BONFIRE_SPI_FLASH_BASE + BONFIRE_SPI_TX, expected);
        received = bonfire_read32(BONFIRE_SPI_FLASH_BASE + BONFIRE_SPI_RX) & 0xffu;
        if (received != expected) {
            printk("SPI loopback test: FAIL tx=0x%x rx=0x%x\n",
                   expected, received);
            return 0;
        }
    }

    printk("SPI loopback test: OK\n");
    return 1;
}

int main(void)
{
    uint32_t uart_divisor = bonfire_uart_divisor();
    uint32_t uart_control = bonfire_uart_control_value(uart_divisor);

    led_out(1u);
    bonfire_uart_init(uart_divisor);
    if ((bonfire_uart_read_control() & BONFIRE_UART_CONTROL_VERIFY_MASK)
            != uart_control) {
        printk("UART test: FAIL\n");
        finish_test(0x0cu);
    }

    led_out(2u);
    report_platform();

    if (!test_gpio()) {
        finish_test(0x0eu);
    }
    led_out(3u);

    if (!test_spi_loopback()) {
        finish_test(0x0du);
    }

    printk("Extended SoC IO test: OK\n");
    finish_test(0x0fu);
}

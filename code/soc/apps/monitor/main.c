#include <stdint.h>

#include <bonfire/console.h>
#include <bonfire/gpio.h>
#include <bonfire/mmio.h>
#include <bonfire/platform.h>
#include <bonfire/spi.h>
#include <bonfire/uart.h>

#define MONITOR_DUMP_WORDS 64u
#define GPIO_TEST_MASK 0xffu
#define GPIO_TIMEOUT_READS 64u

static uint32_t dump_address = BONFIRE_SRAM_BASE;

static char read_char(void)
{
    while ((bonfire_read32(BONFIRE_UART0_BASE + BONFIRE_UART_STATUS) & BONFIRE_UART_STATUS_RX_READY) == 0u) {}

    return (char)bonfire_read32(BONFIRE_UART0_BASE + BONFIRE_UART_TX);
}

static char to_upper(char c)
{
    if (c >= 'a' && c <= 'z') {
        return (char)(c - ('a' - 'A'));
    }

    return c;
}

static int is_space(char c)
{
    return c == ' ' || c == '\t';
}

static int hex_digit_value(char c)
{
    if (c >= '0' && c <= '9') {
        return c - '0';
    }

    c = to_upper(c);
    if (c >= 'A' && c <= 'F') {
        return c - 'A' + 10;
    }

    return -1;
}

static const char *skip_space(const char *text)
{
    while (is_space(*text)) {
        text++;
    }

    return text;
}

static int parse_hex(const char *text, const char **end, uint32_t *value)
{
    uint32_t result = 0;
    int consumed = 0;

    text = skip_space(text);
    if (text[0] == '0' && to_upper(text[1]) == 'X') {
        text += 2;
    }

    while (*text != '\0') {
        int digit = hex_digit_value(*text);

        if (digit < 0) {
            break;
        }

        result = (result << 4) | (uint32_t)digit;
        text++;
        consumed = 1;
    }

    *end = text;
    *value = result;

    return consumed;
}

static int read_line(char *buffer, uint32_t size)
{
    uint32_t pos = 0;
    char c = read_char();

    while (c != '\r' && c != '\n') {
        if ((c == '\b' || c == 0x7f) && pos > 0u) {
            pos--;
            bonfire_uart_puts("\b \b");
        } else if (pos < (size - 1u)) {
            buffer[pos++] = c;
            bonfire_uart_putc(c);
        } else {
            bonfire_uart_putc('\a');
        }

        c = read_char();
    }

    buffer[pos] = '\0';
    bonfire_uart_puts("\n");

    return pos != 0u;
}

static void print_info(void)
{
    uint32_t divisor = bonfire_uart_divisor();
    uint32_t uart_control = bonfire_uart_read_control();
    uint32_t uart_control_divisor = uart_control & BONFIRE_UART_CONTROL_DIVISOR_MASK;
    uint32_t uart_control_extended = (uart_control & BONFIRE_UART_CONTROL_ENABLE_EXTENDED)
                                     >> 16;

    printk("\nBonfire minimal monitor\n");
    printk("platform=%s\n", BONFIRE_PLATFORM_NAME);
    printk("sysclk=%u\n", BONFIRE_SYSCLK_HZ);
    printk("baud=%u\n", BONFIRE_UART_BAUD);
    printk("uart_divisor=%u\n", divisor);
    printk("uart_control=0x%x\n", uart_control);
    printk("  divisor=0x%x (%u)\n", uart_control_divisor, uart_control_divisor);
    printk("  extended_enable=0x%x\n", uart_control_extended);
    printk("sram_base=0x%x\n", BONFIRE_SRAM_BASE);
    printk("sram_size=%u\n", BONFIRE_SRAM_SIZE);
    printk("commands: I=info D [addr]=dump R addr=read W addr value=write\n");
    printk("          G=gpio test S=spi loopback\n");
}

#if BONFIRE_ENABLE_GPIO
static int gpio_wait_for_value(uint32_t expected, uint32_t *actual)
{
    uint32_t timeout;

    for (timeout = 0; timeout < GPIO_TIMEOUT_READS; ++timeout) {
        *actual = bonfire_read32(
            BONFIRE_GPIO_BASE + BONFIRE_GPIO_INPUT_VAL) & GPIO_TEST_MASK;
        if (*actual == expected) {
            return 1;
        }
    }

    return 0;
}
#endif

static void test_gpio(void)
{
#if BONFIRE_ENABLE_GPIO
    static const uint8_t patterns[] = {
        0x00u, 0x01u, 0x02u, 0x04u, 0x08u, 0x10u,
        0x20u, 0x40u, 0x80u, 0x55u, 0xaau, 0xffu,
    };
    uint32_t index;

    printk("GPIO test: start\n");
    bonfire_write32(BONFIRE_GPIO_BASE + BONFIRE_GPIO_OUTPUT_VAL, 0u);
    bonfire_write32(BONFIRE_GPIO_BASE + BONFIRE_GPIO_INPUT_EN,
                    GPIO_TEST_MASK);
    bonfire_write32(BONFIRE_GPIO_BASE + BONFIRE_GPIO_OUTPUT_EN,
                    GPIO_TEST_MASK);

    for (index = 0; index < sizeof(patterns); ++index) {
        uint32_t expected = patterns[index];
        uint32_t actual = 0u;

        bonfire_write32(BONFIRE_GPIO_BASE + BONFIRE_GPIO_OUTPUT_VAL,
                        expected);
        if (!gpio_wait_for_value(expected, &actual)) {
            printk("GPIO test: FAIL pattern=0x%x read=0x%x\n",
                   expected, actual);
            return;
        }
    }

    printk("GPIO test: OK\n");
#else
    printk("GPIO test: unavailable on this platform\n");
#endif
}

static void test_spi_loopback(void)
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
        received = bonfire_read32(
            BONFIRE_SPI_FLASH_BASE + BONFIRE_SPI_RX) & 0xffu;
        if (received != expected) {
            printk("SPI loopback test: FAIL tx=0x%x rx=0x%x\n",
                   expected, received);
            return;
        }
    }

    printk("SPI loopback test: OK\n");
}

static void dump_words(uint32_t address)
{
    uint32_t *words = (uint32_t *)(address & 0xfffffffcu);
    uint32_t index = 0;

    while (index < MONITOR_DUMP_WORDS) {
        if ((index & 3u) == 0u) {
            printk("\n%x    ", (uint32_t)&words[index]);
        }

        printk("%x ", words[index]);
        index++;
    }

    printk("\n");
    dump_address = (uint32_t)&words[MONITOR_DUMP_WORDS];
}

static void read_word(uint32_t address)
{
    address &= 0xfffffffcu;
    printk("R 0x%x = 0x%x\n", address, bonfire_read32(address));
}

static void write_word(uint32_t address, uint32_t value)
{
    address &= 0xfffffffcu;
    bonfire_write32(address, value);
    printk("W 0x%x = 0x%x readback=0x%x\n",
           address, value, bonfire_read32(address));
}

static void handle_command(char *line)
{
    const char *args;
    uint32_t value;
    char command;

    args = skip_space(line);
    command = to_upper(*args);

    if (command == '\0') {
        return;
    }

    args++;
    args = skip_space(args);

    if (command == 'I') {
        print_info();
    } else if (command == 'D') {
        if (parse_hex(args, &args, &value)) {
            dump_address = value & 0xfffffffcu;
        }

        dump_words(dump_address);
    } else if (command == 'R') {
        if (parse_hex(args, &args, &value)) {
            read_word(value);
        } else {
            printk("usage: R <hex-address>\n");
        }
    } else if (command == 'W') {
        uint32_t address;

        if (parse_hex(args, &args, &address)
                && parse_hex(args, &args, &value)) {
            write_word(address, value);
        } else {
            printk("usage: W <hex-address> <hex-value>\n");
        }
    } else if (command == 'G') {
        test_gpio();
    } else if (command == 'S') {
        test_spi_loopback();
    } else {
        printk("\a?\n");
    }
}

int main(void)
{
    char line[64];
    uint32_t uart_divisor = bonfire_uart_divisor();

    bonfire_uart_init(uart_divisor);
    print_info();

    while (1) {
        bonfire_uart_puts("\n>");
        #if defined(BONFIRE_PLATFORM_SIM)
            bonfire_uart_putc(0x1a);
            bonfire_uart_wait_tx_complete();
        #endif
        if (read_line(line, sizeof(line))) {
            handle_command(line);
        }
    }
}

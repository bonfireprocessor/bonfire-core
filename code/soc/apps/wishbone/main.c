#include <stdint.h>

#include <bonfire/mmio.h>
#include <bonfire/platform.h>

int main(void)
{
    volatile uint32_t counter = 10;

    while (counter != 0) {
        counter--;
        bonfire_write32(BONFIRE_WISHBONE_BASE, counter);
        if (bonfire_read32(BONFIRE_WISHBONE_BASE) != 0xdeadbeefu) {
            bonfire_write32(BONFIRE_LED_BASE, 1u);
            while (1) {
            }
        }
    }

    bonfire_write32(BONFIRE_LED_BASE, BONFIRE_LED_MASK);
    while (1) {
    }
}

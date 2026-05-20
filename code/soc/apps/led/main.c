#include <stdint.h>

#include <bonfire/mmio.h>
#include <bonfire/platform.h>

int main(void)
{
    uint32_t counter = 0;

    while (1) {
        bonfire_write32(BONFIRE_LED_BASE, (counter++ >> BONFIRE_LED_SHIFT) & BONFIRE_LED_MASK);
    }
}

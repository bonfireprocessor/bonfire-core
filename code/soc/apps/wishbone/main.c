#include <stdint.h>

#include <bonfire/mmio.h>
#include <bonfire/platform.h>

static uint32_t prng_next(uint32_t *state)
{
    uint32_t x = *state;

    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;

    *state = x;
    return x;
}

int main(void)
{
    uint32_t state = 0x12345678u;

    for (uint32_t i = 0; i < 50u; i++) {
        uint32_t offset = (prng_next(&state) & 0x3fu) << 2;
        uint32_t data = prng_next(&state);
        uintptr_t address = BONFIRE_WISHBONE_BASE + offset;

        bonfire_write32(address, data);
        if (bonfire_read32(address) != data) {
            bonfire_write32(BONFIRE_LED_BASE, 1u);
            bonfire_write32(BONFIRE_LED_BASE, BONFIRE_LED_MASK);
            while (1) {}
        }
    }

    bonfire_write32(BONFIRE_LED_BASE, 2u);
    bonfire_write32(BONFIRE_LED_BASE, BONFIRE_LED_MASK);
    while (1) {}
}

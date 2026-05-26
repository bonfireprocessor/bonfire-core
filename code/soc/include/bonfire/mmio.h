#ifndef BONFIRE_MMIO_H
#define BONFIRE_MMIO_H

#include <stdint.h>

static inline void bonfire_write32(uintptr_t address, uint32_t value)
{
    *((volatile uint32_t *)address) = value;
}

static inline uint32_t bonfire_read32(uintptr_t address)
{
    return *((volatile uint32_t *)address);
}

static inline void bonfire_write8(uintptr_t address, uint8_t value)
{
    *((volatile uint8_t *)address) = value;
}

static inline uint8_t bonfire_read8(uintptr_t address)
{
    return *((volatile uint8_t *)address);
}

#endif

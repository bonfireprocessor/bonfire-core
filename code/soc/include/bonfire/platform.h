#ifndef BONFIRE_PLATFORM_H
#define BONFIRE_PLATFORM_H

#if defined(BONFIRE_PLATFORM_SIM)
#include "../../platforms/sim.h"
#elif defined(BONFIRE_PLATFORM_FIREANT)
#include "../../platforms/fireant.h"
#elif defined(BONFIRE_PLATFORM_ICEPIZERO)
#include "../../platforms/icepizero.h"
#elif defined(BONFIRE_PLATFORM_ULX3S)
#include "../../platforms/ulx3s.h"
#elif defined(BONFIRE_PLATFORM_CMODS7)
#include "../../platforms/cmods7.h"
#else
#error "No BONFIRE_PLATFORM_* define selected"
#endif

#ifndef BONFIRE_LED_MASK
#define BONFIRE_LED_MASK ((1u << BONFIRE_NUM_LEDS) - 1u)
#endif

#ifndef BONFIRE_LED_SHIFT
#define BONFIRE_LED_SHIFT 0u
#endif

#endif

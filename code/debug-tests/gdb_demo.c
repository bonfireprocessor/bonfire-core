#include <stdint.h>

#define VALUE_COUNT 16u
#define STACK_WORDS 256u

typedef struct {
    uint32_t iteration;
    uint32_t checksum;
    uint32_t minimum;
    uint32_t maximum;
} DebugState;

volatile uint32_t debug_stack[STACK_WORDS] __attribute__((aligned(16)));
volatile uint32_t values[VALUE_COUNT];
volatile DebugState debug_state;

int main(void);
void _start(void) __attribute__((naked, noreturn, section(".text.start")));

void _start(void)
{
    __asm__ volatile (
        "la sp, debug_stack\n"
        "addi sp, sp, 1024\n"
        "call main\n"
        "1: j 1b\n"
    );
}

static __attribute__((noinline)) uint32_t rotate_left(uint32_t value, uint32_t amount)
{
    amount &= 31u;
    if (amount == 0u) {
        return value;
    }
    return (value << amount) | (value >> (32u - amount));
}

static __attribute__((noinline)) void initialize_values(uint32_t seed)
{
    uint32_t value = seed;

    for (uint32_t index = 0; index < VALUE_COUNT; ++index) {
        value ^= value << 7;
        value ^= value >> 9;
        value += 0x9e3779b9u + index;
        values[index] = value;
    }
}

static __attribute__((noinline)) void transform_values(uint32_t iteration)
{
    uint32_t previous = values[VALUE_COUNT - 1u];

    for (uint32_t index = 0; index < VALUE_COUNT; ++index) {
        uint32_t current = values[index];
        uint32_t mixed = current + rotate_left(previous, index + iteration);

        if ((mixed & 1u) != 0u) {
            mixed ^= 0xa5a5a5a5u;
        } else {
            mixed += 0x13579bdfu;
        }

        values[index] = mixed;
        previous = current;
    }
}

static __attribute__((noinline)) uint32_t update_statistics(void)
{
    uint32_t checksum = 0x811c9dc5u;
    uint32_t minimum = values[0];
    uint32_t maximum = values[0];

    for (uint32_t index = 0; index < VALUE_COUNT; ++index) {
        uint32_t value = values[index];

        checksum ^= value;
        checksum = rotate_left(checksum, 5u) + 0x01000193u;
        if (value < minimum) {
            minimum = value;
        }
        if (value > maximum) {
            maximum = value;
        }
    }

    debug_state.checksum = checksum;
    debug_state.minimum = minimum;
    debug_state.maximum = maximum;
    return checksum;
}

int main(void)
{
    initialize_values(0x12345678u);
    debug_state.iteration = 0u;

    for (;;) {
        uint32_t iteration = debug_state.iteration + 1u;

        transform_values(iteration);
        update_statistics();
        debug_state.iteration = iteration;
    }
}

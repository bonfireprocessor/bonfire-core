

# bonfire-core uses a riscv64-unknown-elf multilib toolchain (building rv32 targets).
TARGET_PREFIX ?= riscv64-unknown-elf
TARGET_CC := $(TARGET_PREFIX)-gcc
TARGET_LD := $(TARGET_PREFIX)-gcc
TARGET_SIZE := $(TARGET_PREFIX)-size
TARGET_OBJCOPY := $(TARGET_PREFIX)-objcopy
TARGET_OBJDUMP := $(TARGET_PREFIX)-objdump

.PHONY: all soc soc-all clean info

BUILD_DIR ?= build
CORE_TEST_DIR ?= core-tests
CORE_TEST_BUILD_DIR ?= $(BUILD_DIR)/core-tests
DEBUG_TEST_DIR ?= debug-tests
DEBUG_TEST_BUILD_DIR ?= $(BUILD_DIR)/debug-tests
SOC_DIR ?= soc
SOC_APP ?= led
SOC_PLATFORM ?= sim
SOC_BUILD_DIR ?= $(BUILD_DIR)/soc/$(SOC_PLATFORM)

# By default, GNU make deletes intermediate files (like the generated %.elf)
# after building the final target (%.hex). For integration tests that need
# the ELF (e.g., for signature extraction), set KEEP_ELF=1.
ifeq ($(KEEP_ELF),1)
# Keep intermediate files (including generated *.elf) for downstream tooling.
.SECONDARY:
endif


GCC_VERSION := $(shell $(TARGET_CC) -dumpversion | cut -f1 -d.)
ifeq ($(shell echo "$(GCC_VERSION) >= 10" | bc), 1)
    ARCH := rv32i_zicsr
else
    ARCH := rv32i
endif



ABI = ilp32
HEXDUMP ?= hexdump
LINKDEF?=$(CORE_TEST_DIR)/bonfire_core.ld
OBJDUMP_FLAGS := -d -S
CORE_CFLAGS := -march=$(ARCH) -mabi=$(ABI) -g
SOC_CFLAGS := -march=$(ARCH) -mabi=$(ABI) -Og -g -ffreestanding -fno-builtin -Wall -Wextra

SOC_APPS := led wishbone hello
SOC_PLATFORMS := sim icepizero ulx3s cmods7
SOC_PLATFORM_DEFINES_sim := BONFIRE_PLATFORM_SIM
SOC_PLATFORM_DEFINES_icepizero := BONFIRE_PLATFORM_ICEPIZERO
SOC_PLATFORM_DEFINES_ulx3s := BONFIRE_PLATFORM_ULX3S
SOC_PLATFORM_DEFINES_cmods7 := BONFIRE_PLATFORM_CMODS7
SOC_COMMON_SRCS := $(SOC_DIR)/runtime/console.c $(SOC_DIR)/runtime/snprintf.c

$(BUILD_DIR) $(CORE_TEST_BUILD_DIR) $(DEBUG_TEST_BUILD_DIR):
	@mkdir -p $@

# These are freestanding bare-metal programs; do not pull in libc/startup files.
$(CORE_TEST_BUILD_DIR)/%.elf : $(CORE_TEST_DIR)/%.S | $(CORE_TEST_BUILD_DIR)
	@$(TARGET_CC) $(CORE_CFLAGS) -nostdlib -nostartfiles -T$(LINKDEF) -o $@ $<

$(DEBUG_TEST_BUILD_DIR)/%.elf : $(DEBUG_TEST_DIR)/%.S | $(DEBUG_TEST_BUILD_DIR)
	@$(TARGET_CC) $(CORE_CFLAGS) -nostdlib -nostartfiles -T$(CORE_TEST_DIR)/bonfire_core.ld -o $@ $<


$(CORE_TEST_BUILD_DIR)/%.hex : $(CORE_TEST_BUILD_DIR)/%.elf | $(CORE_TEST_BUILD_DIR)
	@$(TARGET_OBJCOPY) -j .text -O binary $< $(basename $@).bin
	@$(HEXDUMP) -v -e '1/4 "%08x\n"' $(basename $@).bin >$@
	@$(TARGET_OBJDUMP) $(OBJDUMP_FLAGS) $< >$(basename $@).lst
	@$(TARGET_OBJDUMP) -t $< >$(basename $@).sym
	$(TARGET_PREFIX)-size  $<

$(DEBUG_TEST_BUILD_DIR)/%.hex : $(DEBUG_TEST_BUILD_DIR)/%.elf | $(DEBUG_TEST_BUILD_DIR)
	@$(TARGET_OBJCOPY) -j .text -O binary $< $(basename $@).bin
	@$(HEXDUMP) -v -e '1/4 "%08x\n"' $(basename $@).bin >$@
	@$(TARGET_OBJDUMP) $(OBJDUMP_FLAGS) $< >$(basename $@).lst
	@$(TARGET_OBJDUMP) -t $< >$(basename $@).sym
	$(TARGET_PREFIX)-size  $<

PROGRAMS := basic_alu simple_loop loop loadsave branch wb_test csr trap
HEXES := $(addprefix $(CORE_TEST_BUILD_DIR)/,$(addsuffix .hex,$(PROGRAMS)))
DEBUG_PROGRAMS := debug endless
DEBUG_HEXES := $(addprefix $(DEBUG_TEST_BUILD_DIR)/,$(addsuffix .hex,$(DEBUG_PROGRAMS)))

define SOC_APP_RULE
$(BUILD_DIR)/soc/$(1)/$(2).elf: $(SOC_DIR)/apps/$(2)/main.c $(SOC_COMMON_SRCS) $(SOC_DIR)/startup/crt0.S $(SOC_DIR)/linker/$(1).ld $(SOC_DIR)/linker/common-sections.ld
	@mkdir -p $$(@D)
	@$$(TARGET_CC) $$(SOC_CFLAGS) -D$$(SOC_PLATFORM_DEFINES_$(1)) -I$$(SOC_DIR)/include -I$$(SOC_DIR)/platforms -nostdlib -nostartfiles -T$$(SOC_DIR)/linker/$(1).ld -Wl,--gc-sections -o $$@ $$(SOC_DIR)/startup/crt0.S $$< $$(SOC_COMMON_SRCS)
endef

$(foreach platform,$(SOC_PLATFORMS),$(foreach app,$(SOC_APPS),$(eval $(call SOC_APP_RULE,$(platform),$(app)))))

$(BUILD_DIR)/soc/%.hex : $(BUILD_DIR)/soc/%.elf
	@$(TARGET_OBJCOPY) -O binary $< $(basename $@).bin
	@$(HEXDUMP) -v -e '1/4 "%08x\n"' $(basename $@).bin >$@
	@$(TARGET_OBJDUMP) $(OBJDUMP_FLAGS) $< >$(basename $@).lst
	@$(TARGET_OBJDUMP) -t $< >$(basename $@).sym
	$(TARGET_PREFIX)-size $<

SOC_HEXES := $(foreach platform,$(SOC_PLATFORMS),$(addprefix $(BUILD_DIR)/soc/$(platform)/,$(addsuffix .hex,$(SOC_APPS))))

all: $(HEXES) $(DEBUG_HEXES) $(SOC_HEXES)

debug-tests: $(DEBUG_HEXES)

soc: $(SOC_BUILD_DIR)/$(SOC_APP).hex

soc-all: $(SOC_HEXES)

clean:
	rm -rf $(BUILD_DIR)

info:
	@echo "GCC version $(GCC_VERSION) detected"
	@echo "Setting ARCH to $(ARCH)"
	@echo "SOC_PLATFORM $(SOC_PLATFORM)"
	@echo "SOC_APP $(SOC_APP)"
    

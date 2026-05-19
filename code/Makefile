

# bonfire-core uses a riscv64-unknown-elf multilib toolchain (building rv32 targets).
TARGET_PREFIX ?= riscv64-unknown-elf
TARGET_CC := $(TARGET_PREFIX)-gcc
TARGET_LD := $(TARGET_PREFIX)-gcc
TARGET_SIZE := $(TARGET_PREFIX)-size
TARGET_OBJCOPY := $(TARGET_PREFIX)-objcopy

BUILD_DIR ?= build

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
LINKDEF?=bonfire_core.ld

$(BUILD_DIR):
	@mkdir -p $@

# These are freestanding bare-metal programs; do not pull in libc/startup files.
$(BUILD_DIR)/%.elf : %.S | $(BUILD_DIR)
	@$(TARGET_CC) -march=$(ARCH) -mabi=$(ABI) -nostdlib -nostartfiles -T$(LINKDEF) -o $@ $<


$(BUILD_DIR)/%.hex : $(BUILD_DIR)/%.elf | $(BUILD_DIR)
	@$(TARGET_OBJCOPY) -j .text -O binary $< $(basename $@).bin
	@$(HEXDUMP) -v -e '1/4 "%08x\n"' $(basename $@).bin >$@
	@$(TARGET_PREFIX)-objdump -d $< >$(basename $@).lst
	@$(TARGET_PREFIX)-objdump -t $< >$(basename $@).sym
	$(TARGET_PREFIX)-size  $<

PROGRAMS := basic_alu simple_loop loop loadsave branch wb_test csr trap
HEXES := $(addprefix $(BUILD_DIR)/,$(addsuffix .hex,$(PROGRAMS)))

all: $(HEXES)

clean:
	rm -rf $(BUILD_DIR)

info:
	@echo "GCC version $(GCC_VERSION) detected"
	@echo "Setting ARCH to $(ARCH)"
    

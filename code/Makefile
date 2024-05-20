

TARGET_PREFIX ?= riscv32-unknown-elf
TARGET_CC := $(TARGET_PREFIX)-gcc
TARGET_LD := $(TARGET_PREFIX)-gcc
TARGET_SIZE := $(TARGET_PREFIX)-size
TARGET_OBJCOPY := $(TARGET_PREFIX)-objcopy


GCC_VERSION := $(shell $(TARGET_CC) -dumpversion | cut -f1 -d.)
ifeq ($(shell echo "$(GCC_VERSION) >= 10" | bc), 1)
    ARCH := rv32i_zicsr
else
    ARCH := rv32i
endif



ABI = ilp32
HEXDUMP ?= hexdump
LINKDEF?=lxp.ld

%.elf : %.S
	$(TARGET_CC) -march=$(ARCH) -mabi=$(ABI)  -nostartfiles -T$(LINKDEF) -o $@ $<


%.hex : %.elf
	$(TARGET_OBJCOPY) -j .text -O binary $< $(basename $@).bin
	$(HEXDUMP) -v -e '1/4 "%08x\n"' $(basename $@).bin >$@
	$(TARGET_PREFIX)-objdump -d $< >$(basename $@).lst
	$(TARGET_PREFIX)-objdump -t $< >$(basename $@).sym
	$(TARGET_PREFIX)-size  $<

basic_alu.hex : basic_alu.S


all: basic_alu.hex simple_loop.hex loop.hex loadsave.hex branch.hex wb_test.hex csr.hex trap.hex endless.hex progbuf.hex
    
	
info:	
	@echo "GCC version $(GCC_VERSION) detected"
	@echo "Setting ARCH to $(ARCH)"
    

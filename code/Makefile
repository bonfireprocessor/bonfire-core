

TARGET_PREFIX ?= riscv32-unknown-elf
TARGET_CC := $(TARGET_PREFIX)-gcc
TARGET_LD := $(TARGET_PREFIX)-gcc
TARGET_SIZE := $(TARGET_PREFIX)-size
TARGET_OBJCOPY := $(TARGET_PREFIX)-objcopy
ARCH= rv32im
ABI = ilp32
HEXDUMP ?= hexdump
LINKDEF?=lxp.ld

%.elf : %.S
	$(TARGET_CC) -march=$(ARCH) -mabi=$(ABI)  -nostartfiles -T$(LINKDEF) -o $@ $<


%.hex : %.elf
	$(TARGET_OBJCOPY) -j .text -O binary $< $(basename $@).bin
	$(HEXDUMP) -v -e '1/4 "%08x\n"' $(basename $@).bin >$@
	$(TARGET_PREFIX)-objdump -d $< >$(basename $@).lst
	$(TARGET_PREFIX)-size  $<

basic_alu.hex : basic_alu.S


all: basic_alu.hex simple_loop.hex

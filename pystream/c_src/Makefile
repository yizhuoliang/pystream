# STREAM Benchmark Makefile
# Supports both standard build and instrumented build

# Default is standard build
BUILD_TYPE ?= standard

# NUMA support (set to 1 to enable)
USE_NUMA ?= 0

# Standard build configuration
STD_CC = gcc
STD_CFLAGS = -O3 -D_GNU_SOURCE
STD_LDFLAGS = -lpthread -lm

# Add NUMA support if enabled
ifeq ($(USE_NUMA),1)
    STD_CFLAGS += -DUSE_NUMA
    STD_LDFLAGS += -lnuma
endif

# Instrumented build configuration (customize as needed)
INST_ROOT_PATH ?= /home/yliang/llvm14-ldb
INST_CC = $(INST_ROOT_PATH)/build/bin/clang
INST_LIBLDB = $(INST_ROOT_PATH)/libldb/libldb.a
INST_CFLAGS = -g -O3 -fno-omit-frame-pointer -fdebug-default-version=3 \
         -I$(INST_ROOT_PATH)/build/lib -I$(INST_ROOT_PATH)/libldb/include \
         -D_GNU_SOURCE
INST_LDFLAGS = -lpthread -rdynamic -lm

# Add NUMA support to instrumented build if enabled
ifeq ($(USE_NUMA),1)
    INST_CFLAGS += -DUSE_NUMA
    INST_LDFLAGS += -lnuma
endif

# Determine which configuration to use
ifeq ($(BUILD_TYPE),instrumented)
    CC = $(INST_CC)
    CFLAGS = $(INST_CFLAGS)
    LDFLAGS = $(INST_LDFLAGS)
    EXTRA_DEPS = $(INST_LIBLDB)
    EXTRA_LINK = $(INST_LIBLDB)
else
    CC = $(STD_CC)
    CFLAGS = $(STD_CFLAGS)
    LDFLAGS = $(STD_LDFLAGS)
    EXTRA_DEPS =
    EXTRA_LINK =
endif

# Target executable
TARGET = stream

all: $(TARGET)

$(TARGET): stream.c $(EXTRA_DEPS)
	$(CC) $(CFLAGS) stream.c $(EXTRA_LINK) $(LDFLAGS) -o $(TARGET)

clean:
	rm -f $(TARGET) *.o

# Show current configuration
info:
	@echo "Build type: $(BUILD_TYPE)"
	@echo "NUMA support: $(USE_NUMA)"
	@echo "Compiler: $(CC)"
	@echo "CFLAGS: $(CFLAGS)"
	@echo "LDFLAGS: $(LDFLAGS)"

# Help message
help:
	@echo "STREAM Benchmark Makefile"
	@echo ""
	@echo "Usage:"
	@echo "  make                  - Build with standard compiler"
	@echo "  make BUILD_TYPE=instrumented - Build with instrumented compiler"
	@echo "  make USE_NUMA=1       - Build with NUMA support"
	@echo "  make clean            - Remove built files"
	@echo "  make info             - Show current build configuration"
	@echo ""
	@echo "Variables:"
	@echo "  BUILD_TYPE            - 'standard' or 'instrumented'"
	@echo "  USE_NUMA              - '0' (disabled) or '1' (enabled)"
	@echo "  INST_ROOT_PATH        - Path to instrumented compiler (for instrumented build)"

.PHONY: all clean info help

## Step 1: Toolchain File

Create the CMake toolchain file for arm-none-eabi cross-compilation:

```cmake
# arm-none-eabi-toolchain.cmake
set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR cortex-m4)

set(CMAKE_C_COMPILER arm-none-eabi-gcc)
set(CMAKE_CXX_COMPILER arm-none-eabi-g++)
set(CMAKE_ASM_COMPILER arm-none-eabi-gcc)
set(CMAKE_OBJCOPY arm-none-eabi-objcopy)
set(CMAKE_SIZE arm-none-eabi-size)

set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)

set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)
```

## Step 2: CMakeLists.txt Header and Toolchain Setup

```cmake
cmake_minimum_required(VERSION 3.20)

set(CMAKE_TOOLCHAIN_FILE
    "${CMAKE_SOURCE_DIR}/arm-none-eabi-toolchain.cmake"
    CACHE FILEPATH "Toolchain file")

project(firmware C ASM)
```

## Step 3: CPU and Compiler Flags

```cmake
set(CPU_FLAGS "-mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard")
set(CMAKE_C_FLAGS "${CPU_FLAGS} -Wall -fdata-sections -ffunction-sections")
set(CMAKE_ASM_FLAGS "${CPU_FLAGS} -x assembler-with-cpp")

# Debug and Release configurations
set(CMAKE_C_FLAGS_DEBUG "-Og -g3 -DDEBUG")
set(CMAKE_C_FLAGS_RELEASE "-Os -DNDEBUG")
```

## Step 4: Source Files and Target

```cmake
# Startup assembly
set(STARTUP_FILE startup_stm32f407xx.s)

# Application sources
file(GLOB_RECURSE APP_SOURCES "Src/*.c")
file(GLOB_RECURSE HAL_SOURCES "Drivers/STM32F4xx_HAL_Driver/Src/*.c")

add_executable(${PROJECT_NAME}.elf
    ${STARTUP_FILE}
    ${APP_SOURCES}
    ${HAL_SOURCES}
)

target_include_directories(${PROJECT_NAME}.elf PRIVATE
    Inc
    Drivers/STM32F4xx_HAL_Driver/Inc
    Drivers/CMSIS/Device/ST/STM32F4xx/Include
    Drivers/CMSIS/Include
)

target_compile_definitions(${PROJECT_NAME}.elf PRIVATE
    USE_HAL_DRIVER
    STM32F407xx
)
```

## Step 5: Linker Script and Post-Build

```cmake
set(LINKER_SCRIPT "${CMAKE_SOURCE_DIR}/STM32F407VGTx_FLASH.ld")

target_link_options(${PROJECT_NAME}.elf PRIVATE
    -T${LINKER_SCRIPT}
    -Wl,--gc-sections
    -Wl,-Map=${PROJECT_NAME}.map
    --specs=nano.specs
    --specs=nosys.specs
)

# Post-build: generate .bin, .hex, and print size
add_custom_command(TARGET ${PROJECT_NAME}.elf POST_BUILD
    COMMAND ${CMAKE_OBJCOPY} -O binary $<TARGET_FILE:${PROJECT_NAME}.elf>
            ${PROJECT_NAME}.bin
    COMMAND ${CMAKE_OBJCOPY} -O ihex $<TARGET_FILE:${PROJECT_NAME}.elf>
            ${PROJECT_NAME}.hex
    COMMAND ${CMAKE_SIZE} $<TARGET_FILE:${PROJECT_NAME}.elf>
    COMMENT "Generating binary and hex files"
)
```

## Build Instructions

```bash
# Debug build
mkdir -p build/debug && cd build/debug
cmake -DCMAKE_BUILD_TYPE=Debug ../..
cmake --build . -j$(nproc)

# Release build
mkdir -p build/release && cd build/release
cmake -DCMAKE_BUILD_TYPE=Release ../..
cmake --build . -j$(nproc)
```

Expected Output: firmware.elf, firmware.bin, firmware.hex, and size report
showing Flash and RAM usage against the CMake configured limits.

## Step 1: I2C Device and Register Map Definition

Output: Register address table with bitfield layout for the SHT30 sensor.

| Register | Address | Size | Description |
|----------|---------|------|-------------|
| TEMP_MSB | 0x00 | 8-bit | Temperature high byte |
| TEMP_LSB | 0x01 | 8-bit | Temperature low byte |
| HUM_MSB | 0x02 | 8-bit | Humidity high byte |
| HUM_LSB | 0x03 | 8-bit | Humidity low byte |
| STATUS | 0x04 | 8-bit | Sensor status flags |
| CONFIG | 0x05 | 8-bit | Configuration register |

```c
#define SHT30_I2C_ADDR       0x44
#define REG_TEMP_MSB          0x00
#define REG_TEMP_LSB          0x01
#define REG_HUM_MSB           0x02
#define REG_HUM_LSB           0x03

typedef struct {
    uint16_t temperature_raw;  /* 14-bit, big-endian from sensor */
    uint16_t humidity_raw;     /* 14-bit, big-endian from sensor */
    uint8_t  status;
} SensorRegisterMap_t;
```

## Step 2: UART Frame Protocol Structure

Output: Protocol frame definition with header, payload, and CRC fields.

```c
#define FRAME_SYNC_BYTE       0xAA
#define MSG_ID_SENSOR_DATA    0x01
#define MSG_ID_SENSOR_CONFIG  0x02

typedef struct __attribute__((packed)) {
    uint8_t  sync;        /* 0xAA */
    uint8_t  msg_id;      /* Message identifier */
    uint8_t  payload_len; /* Length of payload in bytes */
} FrameHeader_t;

typedef struct __attribute__((packed)) {
    int16_t  temperature; /* x100 format, little-endian on wire */
    uint16_t humidity;    /* x100 format, little-endian on wire */
    uint32_t timestamp;   /* Milliseconds since boot */
} SensorPayload_t;

typedef struct __attribute__((packed)) {
    FrameHeader_t   header;
    SensorPayload_t payload;
    uint16_t        crc16;  /* CRC-16/CCITT over header + payload */
} SensorFrame_t;
```

## Step 3: Endianness Handling

1. I2C sensor registers are transmitted in big-endian (MSB first) per SHT30 datasheet
2. UART protocol uses little-endian for multi-byte fields (native STM32 Cortex-M byte order)
3. Conversion macros are required at the I2C read boundary

```c
static inline uint16_t swap_be16(uint16_t val) {
    return (uint16_t)((val >> 8) | (val << 8));
}

static inline int16_t convert_temperature(uint16_t raw_be) {
    uint16_t raw = swap_be16(raw_be);
    return (int16_t)(-4500 + (17500 * (int32_t)raw) / 65535);
}

static inline uint16_t convert_humidity(uint16_t raw_be) {
    uint16_t raw = swap_be16(raw_be);
    return (uint16_t)((10000 * (uint32_t)raw) / 65535);
}
```

## Step 4: Validation Rules

1. Temperature raw value must be within valid 14-bit range (0x0000-0x3FFF)
2. Humidity raw value must be within valid 14-bit range (0x0000-0x3FFF)
3. Converted temperature must be in range -4000 to 12500 (x100 format)
4. Converted humidity must be in range 0 to 10000 (x100 format)
5. CRC-16 must match computed value over header + payload bytes

```c
typedef enum {
    VALIDATE_OK = 0,
    VALIDATE_ERR_TEMP_RANGE,
    VALIDATE_ERR_HUM_RANGE,
    VALIDATE_ERR_CRC_MISMATCH
} ValidateResult_t;

ValidateResult_t validate_sensor_frame(const SensorFrame_t *frame);
```

## Summary

- Register map defines 6 registers with clear address and size specifications
- Protocol frame uses packed structures for deterministic wire layout
- Endianness boundary is explicitly handled at the I2C-to-UART conversion layer
- Validation covers both raw sensor ranges and CRC integrity checks

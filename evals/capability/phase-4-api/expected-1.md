## Step 1: Packet Format Definition

The serial protocol uses a fixed-header, variable-payload frame structure.

```
+--------+--------+--------+--------+---------+--------+--------+
| SYNC_1 | SYNC_2 | CMD_ID | LENGTH | PAYLOAD | CRC_LO | CRC_HI |
| 0xAA   | 0x55   | 1 byte | 1 byte | N bytes | 1 byte | 1 byte |
+--------+--------+--------+--------+---------+--------+--------+
```

```c
#define SYNC_BYTE_1  0xAA
#define SYNC_BYTE_2  0x55
#define MAX_PAYLOAD  256

typedef struct __attribute__((packed)) {
    uint8_t  sync1;
    uint8_t  sync2;
    uint8_t  cmd_id;
    uint8_t  length;     /* payload length */
    uint8_t  payload[MAX_PAYLOAD];
    uint16_t crc16;      /* CRC-16/CCITT, little-endian */
} SerialPacket_t;
```

## Step 2: Command Code Table

| CMD_ID | Name | Direction | Payload (request) | Payload (response) | Timeout |
|--------|------|-----------|--------------------|--------------------|---------|
| 0x01 | READ_SENSOR | PC -> MCU | None (length=0) | temp(2B) + hum(2B) + pres(2B) | 500ms |
| 0x02 | SET_CONFIG | PC -> MCU | config_id(1B) + value(4B) | status(1B) | 2000ms |
| 0x03 | GET_FW_INFO | PC -> MCU | None (length=0) | version(3B) + build_date(4B) | 500ms |
| 0x80 | ERROR_RESP | MCU -> PC | error_code(1B) + detail(2B) | N/A | N/A |

```c
typedef enum {
    CMD_READ_SENSOR  = 0x01,
    CMD_SET_CONFIG   = 0x02,
    CMD_GET_FW_INFO  = 0x03,
    CMD_ERROR_RESP   = 0x80
} CommandId_t;
```

## Step 3: Request/Response Sequences

1. PC sends request packet with command ID and optional payload
2. MCU validates sync bytes and CRC before processing
3. MCU sends response with same command ID and response payload
4. If MCU detects an error, it sends 0x80 (ERROR_RESP) instead

**Read Sensor Sequence:**
```
PC  --[AA 55 01 00 xx xx]--> MCU     (request: read sensor)
PC  <--[AA 55 01 06 data crc]-- MCU  (response: 6 bytes sensor data)
```

**Set Config Sequence:**
```
PC  --[AA 55 02 05 id val crc]--> MCU   (request: set config)
PC  <--[AA 55 02 01 status crc]-- MCU   (response: 1 byte status)
```

**Error Response Sequence:**
```
PC  --[AA 55 FF 00 crc]--> MCU          (request: invalid command)
PC  <--[AA 55 80 03 err detail crc]-- MCU (response: error)
```

## Step 4: Error Codes and Handling

| Error Code | Name | Description | Retry |
|------------|------|-------------|-------|
| 0x00 | ERR_NONE | No error | N/A |
| 0x01 | ERR_INVALID_CMD | Unknown command ID | No |
| 0x02 | ERR_CRC_MISMATCH | CRC verification failed | Yes (max 3) |
| 0x03 | ERR_TIMEOUT | MCU processing timeout | Yes (max 2) |
| 0x04 | ERR_SENSOR_FAIL | Sensor read failure | Yes (max 3) |
| 0x05 | ERR_PAYLOAD_LEN | Invalid payload length | No |
| 0x06 | ERR_CONFIG_RANGE | Config value out of range | No |

```c
typedef enum {
    ERR_NONE          = 0x00,
    ERR_INVALID_CMD   = 0x01,
    ERR_CRC_MISMATCH  = 0x02,
    ERR_TIMEOUT       = 0x03,
    ERR_SENSOR_FAIL   = 0x04,
    ERR_PAYLOAD_LEN   = 0x05,
    ERR_CONFIG_RANGE  = 0x06
} ErrorCode_t;
```

## Step 5: Timeout and Retry Policy

1. Normal commands (READ_SENSOR, GET_FW_INFO): 500ms timeout
2. Configuration commands (SET_CONFIG): 2000ms timeout (flash write delay)
3. CRC mismatch and sensor failure: retry up to 3 times with 100ms back-off
4. Timeout errors: retry up to 2 times with 200ms back-off
5. Invalid command and payload errors: no retry, report to application layer
6. After max retries exhausted, serial link is marked as degraded and reconnect is initiated

## Summary

- Fixed-header serial packet format with sync detection and CRC-16 integrity
- Three command endpoints covering sensor reading, configuration, and firmware info
- Request/response protocol with explicit error codes and retry policies
- Timeout values differentiated by command type for optimal responsiveness

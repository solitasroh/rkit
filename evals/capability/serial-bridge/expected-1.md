## Step 1: Packet Structure Definition

MCU-side packet format (C):

```c
#define STX  0x02
#define ETX  0x03
#define MAX_PAYLOAD_SIZE  128

typedef struct __attribute__((packed)) {
    uint8_t  stx;        /* Start of frame: 0x02 */
    uint8_t  cmd_id;     /* Command identifier */
    uint8_t  seq_num;    /* Sequence number for request/response matching */
    uint16_t payload_len;
    uint8_t  payload[MAX_PAYLOAD_SIZE];
    uint16_t crc16;      /* CRC16-CCITT over cmd_id..payload */
    uint8_t  etx;        /* End of frame: 0x03 */
} Packet_t;
```

## Step 2: CRC16-CCITT Calculation

```c
uint16_t CRC16_Calculate(const uint8_t *data, uint16_t length)
{
    uint16_t crc = 0xFFFF;

    for (uint16_t i = 0; i < length; i++)
    {
        crc ^= (uint16_t)data[i] << 8;
        for (uint8_t bit = 0; bit < 8; bit++)
        {
            if (crc & 0x8000)
                crc = (crc << 1) ^ 0x1021;
            else
                crc <<= 1;
        }
    }
    return crc;
}
```

## Step 3: MCU Serial Send with Framing

```c
static uint8_t tx_seq_num = 0;

HAL_StatusTypeDef Serial_SendPacket(uint8_t cmd_id,
                                     const uint8_t *payload,
                                     uint16_t payload_len)
{
    Packet_t pkt;
    pkt.stx = STX;
    pkt.cmd_id = cmd_id;
    pkt.seq_num = tx_seq_num++;
    pkt.payload_len = payload_len;
    memcpy(pkt.payload, payload, payload_len);

    /* CRC over cmd_id + seq_num + payload_len + payload */
    uint16_t crc_len = 1 + 1 + 2 + payload_len;
    pkt.crc16 = CRC16_Calculate(&pkt.cmd_id, crc_len);
    pkt.etx = ETX;

    uint16_t total = 1 + crc_len + 2 + 1;  /* STX + data + CRC + ETX */
    return HAL_UART_Transmit(&huart2, (uint8_t *)&pkt, total, 100);
}
```

## Step 4: MCU Serial Receive and Parse

```c
typedef enum {
    PARSE_WAIT_STX,
    PARSE_HEADER,
    PARSE_PAYLOAD,
    PARSE_CRC_ETX,
} ParseState_t;

bool Serial_ParseByte(uint8_t byte, Packet_t *result)
{
    static ParseState_t state = PARSE_WAIT_STX;
    static Packet_t rx_pkt;
    static uint16_t rx_idx = 0;

    switch (state)
    {
    case PARSE_WAIT_STX:
        if (byte == STX) {
            rx_pkt.stx = STX;
            state = PARSE_HEADER;
            rx_idx = 0;
        }
        break;

    case PARSE_HEADER:
        /* Parse cmd_id, seq_num, payload_len */
        /* ... header bytes collection ... */
        state = PARSE_PAYLOAD;
        break;

    case PARSE_PAYLOAD:
        /* Collect payload bytes */
        if (rx_idx >= rx_pkt.payload_len)
            state = PARSE_CRC_ETX;
        break;

    case PARSE_CRC_ETX:
        /* Validate CRC and ETX, copy to result if valid */
        if (byte == ETX) {
            uint16_t calc_crc = CRC16_Calculate(&rx_pkt.cmd_id,
                1 + 1 + 2 + rx_pkt.payload_len);
            if (calc_crc == rx_pkt.crc16) {
                memcpy(result, &rx_pkt, sizeof(Packet_t));
                state = PARSE_WAIT_STX;
                return true;
            }
        }
        state = PARSE_WAIT_STX;
        break;
    }
    return false;
}
```

## Step 5: WPF-Side Response Handling (C#)

```csharp
public class SerialBridge
{
    private readonly SerialPort _port;
    private byte _seqNum = 0;
    private const int RetryCount = 3;
    private const int TimeoutMs = 500;

    public async Task<byte[]> SendCommandAsync(byte cmdId, byte[] payload)
    {
        var packet = BuildPacket(cmdId, _seqNum++, payload);

        for (int retry = 0; retry < RetryCount; retry++)
        {
            _port.Write(packet, 0, packet.Length);

            var response = await WaitForResponseAsync(cmdId, TimeoutMs);
            if (response != null)
                return response;
        }

        throw new TimeoutException($"No response for cmd 0x{cmdId:X2}");
    }

    private async Task<byte[]> WaitForResponseAsync(byte cmdId, int timeoutMs)
    {
        var cts = new CancellationTokenSource(timeoutMs);
        /* Read serial bytes, parse STX/ETX framing, validate CRC */
        /* Return payload if request/response sequence matches */
        return null;
    }
}
```

## Protocol Design Notes
- STX/ETX framing allows recovery from partial or corrupted packets
- CRC16-CCITT provides reliable error detection for serial transmission
- Sequence numbers enable matching each request to its response
- Retry with timeout (500ms x 3) handles transient communication failures
- Both MCU and WPF must use identical CRC polynomial (0x1021, init 0xFFFF)

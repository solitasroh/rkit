## Step 1: Communication Abstraction Interface

Define a common interface for all protocols:

```c
typedef enum {
    COMM_PROTO_UART,
    COMM_PROTO_SPI,
    COMM_PROTO_I2C,
} CommProtocol_t;

typedef struct {
    CommProtocol_t protocol;
    HAL_StatusTypeDef (*init)(void);
    HAL_StatusTypeDef (*transmit)(const uint8_t *data, uint16_t len);
    HAL_StatusTypeDef (*receive)(uint8_t *data, uint16_t len, uint32_t timeout);
    void (*deinit)(void);
} CommInterface_t;

static const CommInterface_t comm_drivers[];
```

## Step 2: UART DMA Transmit with Interrupt Callback

```c
#define UART_TX_BUF_SIZE  256
static uint8_t uart_tx_buf[UART_TX_BUF_SIZE];
static volatile uint8_t uart_tx_complete = 1;

HAL_StatusTypeDef UART_DMA_Transmit(const uint8_t *data, uint16_t len)
{
    if (!uart_tx_complete || len > UART_TX_BUF_SIZE)
        return HAL_BUSY;

    memcpy(uart_tx_buf, data, len);
    uart_tx_complete = 0;

    return HAL_UART_Transmit_DMA(&huart2, uart_tx_buf, len);
}

void HAL_UART_TxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance == USART2)
    {
        uart_tx_complete = 1;
    }
}
```

## Step 3: SPI DMA Full-Duplex Transfer

```c
#define SPI_BUF_SIZE  64
static uint8_t spi_tx_buf[SPI_BUF_SIZE];
static uint8_t spi_rx_buf[SPI_BUF_SIZE];
static volatile uint8_t spi_transfer_complete = 1;

HAL_StatusTypeDef SPI_DMA_Transfer(const uint8_t *tx, uint8_t *rx, uint16_t len)
{
    if (!spi_transfer_complete || len > SPI_BUF_SIZE)
        return HAL_BUSY;

    memcpy(spi_tx_buf, tx, len);
    spi_transfer_complete = 0;

    HAL_GPIO_WritePin(SPI_CS_GPIO_Port, SPI_CS_Pin, GPIO_PIN_RESET);
    return HAL_SPI_TransmitReceive_DMA(&hspi1, spi_tx_buf, spi_rx_buf, len);
}

void HAL_SPI_TxRxCpltCallback(SPI_HandleTypeDef *hspi)
{
    if (hspi->Instance == SPI1)
    {
        HAL_GPIO_WritePin(SPI_CS_GPIO_Port, SPI_CS_Pin, GPIO_PIN_SET);
        spi_transfer_complete = 1;
    }
}
```

## Step 4: I2C Interrupt-Based Receive

```c
HAL_StatusTypeDef I2C_IT_Read(uint16_t dev_addr, uint8_t reg,
                               uint8_t *data, uint16_t len)
{
    HAL_StatusTypeDef status;

    /* Write register address first */
    status = HAL_I2C_Master_Transmit_IT(&hi2c1, dev_addr << 1, &reg, 1);
    if (status != HAL_OK)
        return status;

    /* Wait for transmit complete with timeout */
    uint32_t tick = HAL_GetTick();
    while (HAL_I2C_GetState(&hi2c1) != HAL_I2C_STATE_READY)
    {
        if ((HAL_GetTick() - tick) > 100)
            return HAL_TIMEOUT;
    }

    /* Read data with interrupt */
    return HAL_I2C_Master_Receive_IT(&hi2c1, dev_addr << 1, data, len);
}
```

## Step 5: Driver Registration and Protocol Switching

```c
static const CommInterface_t comm_drivers[] = {
    [COMM_PROTO_UART] = {
        .protocol = COMM_PROTO_UART,
        .init     = UART_Init,
        .transmit = UART_DMA_Transmit,
        .receive  = UART_Receive,
        .deinit   = UART_DeInit,
    },
    [COMM_PROTO_SPI] = {
        .protocol = COMM_PROTO_SPI,
        .init     = SPI_Init,
        .transmit = SPI_DMA_Transmit,
        .receive  = SPI_DMA_Receive,
        .deinit   = SPI_DeInit,
    },
    [COMM_PROTO_I2C] = {
        .protocol = COMM_PROTO_I2C,
        .init     = I2C_Init,
        .transmit = I2C_Transmit,
        .receive  = I2C_IT_Receive,
        .deinit   = I2C_DeInit,
    },
};

HAL_StatusTypeDef Comm_Read(CommProtocol_t proto, uint8_t *buf, uint16_t len)
{
    return comm_drivers[proto].receive(buf, len, 1000);
}
```

## Error Handling Notes
- Each function returns HAL_StatusTypeDef for unified error reporting
- DMA callbacks set completion flags checked before new transfers
- I2C uses polling with timeout to prevent indefinite blocking
- Retry logic can be added at the Comm_Read/Comm_Write abstraction level

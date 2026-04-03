## Step 1: DMA Buffer and Handle Setup

Define the DMA circular receive buffer and UART handle:

```c
#define UART_RX_BUF_SIZE  1024

static uint8_t uart_rx_dma_buf[UART_RX_BUF_SIZE];
static uint16_t rx_head = 0;
static UART_HandleTypeDef huart2;
static QueueHandle_t rx_queue;
```

## Step 2: DMA Initialization

Configure DMA for circular mode and start the receive:

```c
void UART_DMA_Init(void)
{
    /* Enable DMA1 clock */
    __HAL_RCC_DMA1_CLK_ENABLE();

    /* Start DMA receive with idle line detection */
    HAL_UARTEx_ReceiveToIdle_DMA(&huart2, uart_rx_dma_buf, UART_RX_BUF_SIZE);

    /* Disable half-transfer interrupt (optional, reduces overhead) */
    __HAL_DMA_DISABLE_IT(huart2.hdmarx, DMA_IT_HT);
}
```

## Step 3: HAL_UARTEx_RxEventCallback Implementation

Process received data in the callback with circular buffer wrapping:

```c
void HAL_UARTEx_RxEventCallback(UART_HandleTypeDef *huart, uint16_t Size)
{
    if (huart->Instance == USART2)
    {
        const uint16_t new_head = Size;
        uint16_t length;

        /* Calculate received length with wrap-around */
        if (new_head >= rx_head)
        {
            length = new_head - rx_head;
        }
        else
        {
            length = UART_RX_BUF_SIZE - rx_head + new_head;
        }

        /* Overflow protection: check queue space before sending */
        if (uxQueueSpacesAvailable(rx_queue) > 0)
        {
            RxFrame_t frame;
            frame.offset = rx_head;
            frame.length = length;
            xQueueSendFromISR(rx_queue, &frame, NULL);
        }

        rx_head = new_head;

        /* Restart DMA reception */
        HAL_UARTEx_ReceiveToIdle_DMA(&huart2, uart_rx_dma_buf, UART_RX_BUF_SIZE);
        __HAL_DMA_DISABLE_IT(huart2.hdmarx, DMA_IT_HT);
    }
}
```

## Step 4: Error Handling

Handle UART errors to recover from noise/framing issues:

```c
void HAL_UART_ErrorCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance == USART2)
    {
        /* Clear error flags and restart DMA */
        __HAL_UART_CLEAR_OREFLAG(huart);
        HAL_UARTEx_ReceiveToIdle_DMA(huart, uart_rx_dma_buf, UART_RX_BUF_SIZE);
    }
}
```

## Step 5: FreeRTOS Consumer Task

```c
void vUartProcessTask(void *pvParameters)
{
    RxFrame_t frame;
    for (;;)
    {
        if (xQueueReceive(rx_queue, &frame, portMAX_DELAY) == pdTRUE)
        {
            /* Process received data from circular buffer */
            ProcessData(&uart_rx_dma_buf[frame.offset], frame.length);
        }
    }
}
```

## Safety Considerations and Input Validation
- DMA circular mode avoids buffer overrun at the hardware level
- Idle line detection ensures variable-length packet boundaries are preserved
- Queue overflow protection prevents data corruption under peak load
- Error callback ensures recovery from UART framing/noise errors
- Input validation: verify Size parameter bounds before buffer access (Size <= UART_RX_BUF_SIZE)
- Buffer pointer validation: check rx_head does not exceed buffer boundary after wrap-around

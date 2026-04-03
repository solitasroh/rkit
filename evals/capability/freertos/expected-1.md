## Step 1: Queue and Task Handle Definitions

```c
#define SENSOR_TASK_STACK_SIZE  256  /* words = 1024 bytes */
#define COMM_TASK_STACK_SIZE    512  /* words = 2048 bytes, UART needs more */
#define SENSOR_QUEUE_LENGTH     10
#define SENSOR_READ_PERIOD_MS   100

typedef struct {
    float temperature;
    uint32_t timestamp;
} SensorData_t;

static QueueHandle_t xSensorQueue;
static TaskHandle_t xSensorTaskHandle;
static TaskHandle_t xCommTaskHandle;
```

## Step 2: Queue Creation

```c
void App_Init(void)
{
    xSensorQueue = xQueueCreate(SENSOR_QUEUE_LENGTH, sizeof(SensorData_t));
    configASSERT(xSensorQueue != NULL);

    xTaskCreate(vSensorTask, "Sensor", SENSOR_TASK_STACK_SIZE,
                NULL, 3, &xSensorTaskHandle);  /* Priority 3 - higher */

    xTaskCreate(vCommTask, "Comm", COMM_TASK_STACK_SIZE,
                NULL, 2, &xCommTaskHandle);     /* Priority 2 - lower */
}
```

## Step 3: Sensor Read Task

```c
void vSensorTask(void *pvParameters)
{
    TickType_t xLastWakeTime = xTaskGetTickCount();
    SensorData_t data;

    for (;;)
    {
        /* Read I2C temperature sensor with timeout */
        if (I2C_ReadTemperature(&data.temperature, pdMS_TO_TICKS(10)) == HAL_OK)
        {
            data.timestamp = xTaskGetTickCount();

            /* Send to queue with timeout to prevent deadlock */
            xQueueSend(xSensorQueue, &data, pdMS_TO_TICKS(50));
        }

        /* Kick watchdog */
        HAL_IWDG_Refresh(&hiwdg);

        /* Precise periodic execution */
        vTaskDelayUntil(&xLastWakeTime, pdMS_TO_TICKS(SENSOR_READ_PERIOD_MS));
    }
}
```

## Step 4: Communication Task

```c
void vCommTask(void *pvParameters)
{
    SensorData_t data;
    char tx_buf[64];

    for (;;)
    {
        /* Receive from queue with timeout to avoid deadlock */
        if (xQueueReceive(xSensorQueue, &data, pdMS_TO_TICKS(500)) == pdTRUE)
        {
            snprintf(tx_buf, sizeof(tx_buf),
                     "T=%.2f,ts=%lu\r\n", data.temperature, data.timestamp);

            HAL_UART_Transmit(&huart2, (uint8_t *)tx_buf, strlen(tx_buf),
                              pdMS_TO_TICKS(100));
        }

        /* Kick watchdog even if no data received */
        HAL_IWDG_Refresh(&hiwdg);
    }
}
```

## Step 5: Stack Size Calculation

Stack sizing rationale:
- Sensor task: 256 words (1024 bytes) - minimal local variables, I2C HAL usage
- Comm task: 512 words (2048 bytes) - snprintf buffer, UART HAL requires more stack
- Total: 1024 + 2048 + queue overhead (~200 bytes) = ~3.3KB
- Fits within the 20KB available budget

Use `uxTaskGetStackHighWaterMark()` at runtime to verify actual usage
and adjust stack sizes if high water mark is below 20% of allocation.

## Safety Considerations
- All xQueueSend/xQueueReceive calls use finite timeouts, never portMAX_DELAY
- Priority inversion is avoided by giving sensor task higher priority
- configCHECK_FOR_STACK_OVERFLOW set to 2 for runtime detection
- Watchdog refresh in both task loops ensures system recovery on hang

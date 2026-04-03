## Step 1: Clock Enable

Enable clocks for the SPI peripheral and GPIO port:

```c
#include "fsl_clock.h"
#include "fsl_port.h"
#include "fsl_gpio.h"
#include "fsl_dspi.h"

void Board_InitPeripherals(void)
{
    /* Enable clock for PORTD and SPI0 */
    CLOCK_EnableClock(kCLOCK_PortD);
    CLOCK_EnableClock(kCLOCK_Spi0);
}
```

## Step 2: Pin Mux Configuration

Configure PORTD pins for SPI0 function and GPIO chip select:

```c
void Board_InitPins(void)
{
    /* SPI0 pin mux: ALT2 for DSPI function */
    PORT_SetPinMux(PORTD, 0U, kPORT_MuxAlt2);  /* SPI0_SCK  */
    PORT_SetPinMux(PORTD, 1U, kPORT_MuxAlt2);  /* SPI0_MOSI */
    PORT_SetPinMux(PORTD, 2U, kPORT_MuxAlt2);  /* SPI0_MISO */

    /* CS pin as GPIO output (manual control) */
    PORT_SetPinMux(PORTD, 3U, kPORT_MuxAsGpio);
}
```

## Step 3: GPIO Chip Select Setup

```c
void CS_GPIO_Init(void)
{
    const gpio_pin_config_t cs_config = {
        .pinDirection = kGPIO_DigitalOutput,
        .outputLogic  = 1U  /* CS idle high */
    };

    GPIO_PinInit(GPIOD, 3U, &cs_config);
}

static inline void CS_Assert(void)   { GPIO_PortClear(GPIOD, 1U << 3); }
static inline void CS_Deassert(void) { GPIO_PortSet(GPIOD, 1U << 3);   }
```

## Step 4: SPI Master Initialization

```c
void SPI_Master_Init(void)
{
    dspi_master_config_t masterConfig;

    DSPI_MasterGetDefaultConfig(&masterConfig);
    masterConfig.ctarConfig.baudRate        = 1000000U;  /* 1 MHz */
    masterConfig.ctarConfig.bitsPerFrame    = 8U;
    masterConfig.ctarConfig.cpol            = kDSPI_ClockPolarityActiveHigh;
    masterConfig.ctarConfig.cpha            = kDSPI_ClockPhaseFirstEdge;
    masterConfig.whichPcs                   = kDSPI_Pcs0;
    masterConfig.pcsActiveHighOrLow         = kDSPI_PcsActiveLow;

    uint32_t srcClock_Hz = CLOCK_GetBusClkFreq();
    DSPI_MasterInit(SPI0, &masterConfig, srcClock_Hz);
}
```

## Step 5: SPI Transfer Function

```c
status_t SPI_ReadADC(uint8_t channel, uint16_t *value)
{
    uint8_t tx[3] = {0x06 | (channel >> 2), (channel & 0x03) << 6, 0x00};
    uint8_t rx[3] = {0};

    dspi_transfer_t xfer;
    xfer.txData   = tx;
    xfer.rxData   = rx;
    xfer.dataSize = 3U;
    xfer.configFlags = kDSPI_MasterCtar0;

    CS_Assert();
    status_t status = DSPI_MasterTransferBlocking(SPI0, &xfer);
    CS_Deassert();

    if (status == kStatus_Success)
    {
        *value = ((rx[1] & 0x0F) << 8) | rx[2];
    }
    return status;
}
```

## Setup Summary
- CLOCK_EnableClock for peripheral and port clocks
- PORT_SetPinMux for SPI alternate function and GPIO
- DSPI_MasterInit with config structure for bus speed and polarity
- Manual GPIO CS control for flexible chip select timing

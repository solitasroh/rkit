NXP Kinetis K SDK GPIO + SPI driver initialization using fsl_* APIs.

## Requirements
- Clock configuration for SPI0 and PORTD using fsl_clock.h
- Pin mux setup for SPI0 (SCK, MOSI, MISO, CS) on PORTD pins using fsl_port.h
- GPIO output for chip select (manual CS control)
- SPI master initialization at 1 MHz using fsl_dspi.h
- CMSIS-style register access patterns where needed

## Context
Target is NXP MK64FN1M0VLL12 (Kinetis K64) on a FRDM-K64F board.
SPI0 connects to an external ADC (MCP3208) for analog sensor reading.
PORTD[0]=SCK, PORTD[1]=MOSI, PORTD[2]=MISO, PORTD[3]=CS (GPIO manual).
System clock is 120 MHz, bus clock is 60 MHz.

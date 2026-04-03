MCU sensor data real-time monitoring WPF dashboard mockup with MVVM architecture.

## Requirements
- Display temperature, humidity, and pressure readings from MCU via serial port
- Components: RadialGauge (current values), LineChart (time-series trend), StatusLed (connection status), CommandPanel (start/stop/reset)
- Responsive layout with Grid-based panel arrangement
- Dark theme optimized for industrial monitoring use case

## Context
The dashboard receives sensor data at 10Hz from an STM32 MCU over UART serial connection.
It must display real-time gauges, historical trend charts (last 5 minutes), and device connection status.
The operator needs a command panel to start/stop data acquisition and reset the MCU.
Target framework is WPF .NET 8 with CommunityToolkit.Mvvm for MVVM pattern.

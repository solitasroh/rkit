WPF ViewModel with SerialPort data receive, ObservableProperty binding, and UI auto-update.

## Requirements
- SerialPort wrapper service with async data receive
- ViewModel binding using CommunityToolkit.Mvvm [ObservableProperty] attributes
- Thread marshaling via Dispatcher for UI updates from serial receive callback
- Disconnect detection and automatic reconnect logic with exponential back-off
- Clean disposal of serial resources on application shutdown

## Context
A WPF .NET 8 application receives sensor data from an STM32 MCU at 10Hz over COM port.
The ViewModel must update UI-bound properties on the UI thread while serial data arrives on a background thread.
The serial connection may drop due to USB disconnect or MCU reset, requiring automatic reconnect.
CommunityToolkit.Mvvm is used for MVVM pattern. ViewModel must NOT reference System.Windows.Controls.

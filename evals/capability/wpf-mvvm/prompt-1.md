WPF .NET 8 ViewModel for sensor data display using CommunityToolkit.Mvvm.

## Requirements
- ViewModel inheriting ObservableObject
- [ObservableProperty] for sensor data fields (temperature, humidity, status)
- [RelayCommand] for refresh and reset actions
- Dependency injection via constructor for ISensorService
- Must NOT use {x:Bind} (UWP/WinUI only, not WPF)
- Must NOT reference System.Windows.Controls in ViewModel

## Context
Desktop monitoring application for embedded sensor data received via serial port.
The ViewModel drives a dashboard view showing real-time temperature, humidity,
and connection status. Data updates arrive via ISensorService which abstracts
the serial communication layer. The format follows CommunityToolkit.Mvvm
source generator pattern for .NET 8 with partial classes.

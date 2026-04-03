MCU serial monitoring desktop app project structure with WPF .NET 8 and WinUI3 migration path.

## Requirements
- WPF .NET 8 project with CommunityToolkit.Mvvm for MVVM pattern
- DI container using Microsoft.Extensions.DependencyInjection
- SerialPort service abstraction with interface for testability
- MVVM folder structure (Views, ViewModels, Services, Models)
- No x:Bind (WPF only, not WinUI), ViewModel must not reference System.Windows.Controls
- WinUI3 migration compatibility notes

## Context
The desktop application monitors sensor data from STM32 MCU devices over serial port.
It displays real-time gauge, chart, and status indicators on a WPF dashboard.
The project must be structured for future WinUI3 migration with minimal code changes.
DI is used for service abstraction, making ViewModels testable without hardware dependency.
Target audience is embedded engineers who need a PC-side monitoring tool.

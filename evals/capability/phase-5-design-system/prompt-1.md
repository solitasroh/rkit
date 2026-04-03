MCU control WPF/WinUI3 component library design system for industrial sensor monitoring.

## Requirements
- Core components: RadialGauge, LineChart, StatusLed, CommandButton
- Design tokens for colors, typography, spacing (dark/light theme support)
- ResourceDictionary structure with theme separation
- Component interface specifications with dependency properties
- WinUI3 migration compatibility considerations

## Context
The component library serves a WPF .NET 8 desktop application that monitors and controls MCU devices.
Components must be reusable across multiple monitoring dashboards with consistent visual identity.
The design system must support dark theme (default for industrial use) and light theme.
Future migration to WinUI3 is planned, so component APIs should avoid WPF-only constructs where possible.

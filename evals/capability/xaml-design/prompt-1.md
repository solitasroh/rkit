WPF XAML DataTemplate + Style + Converter for sensor data visualization.

## Requirements
- StatusLed indicator with color states: green (normal), yellow (warning), red (alarm)
- DataTemplate for sensor item display with name, value, unit, and status LED
- Style with DataTriggers for status-based visual changes
- IValueConverter for temperature to color gradient mapping
- ResourceDictionary organization for reusable sensor UI components

## Context
The sensor monitoring dashboard displays a list of sensor readings.
Each sensor has a name, current value, unit, and status enum (Normal/Warning/Alarm).
The StatusLed is an Ellipse that changes color based on the sensor status.
A temperature gauge background also shifts from blue (cold) through green (normal)
to red (hot) using a value converter. All styles should be in a shared
ResourceDictionary for use across multiple views.

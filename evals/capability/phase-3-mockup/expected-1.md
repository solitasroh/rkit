## Step 1: Dashboard Layout Structure

The dashboard follows a Grid-based panel layout pattern with three main zones.
This template uses a 3-column, 2-row format optimized for widescreen monitors.

```
+--------------------------------------------------+
|  Header Bar (Connection Status + Title)           |
+----------------+-------------------+--------------+
|  RadialGauge   |  RadialGauge      | RadialGauge  |
|  Temperature   |  Humidity         | Pressure     |
+----------------+-------------------+--------------+
|  LineChart (Time-Series Trend - Full Width)       |
+--------------------------------------------------+
|  CommandPanel (Start | Stop | Reset | Settings)   |
+--------------------------------------------------+
```

## Step 2: XAML Component Placement

Each component follows a consistent format using UserControl encapsulation.
The RadialGauge pattern uses an Arc + TextBlock composition.

```xml
<Window x:Class="SensorMonitor.MainWindow">
  <Grid>
    <Grid.RowDefinitions>
      <RowDefinition Height="48"/>
      <RowDefinition Height="*"/>
      <RowDefinition Height="2*"/>
      <RowDefinition Height="60"/>
    </Grid.RowDefinitions>

    <!-- Header with StatusLed -->
    <StackPanel Grid.Row="0" Orientation="Horizontal">
      <Ellipse Width="12" Height="12"
               Fill="{Binding ConnectionStatusBrush}"/>
      <TextBlock Text="{Binding ConnectionLabel}"/>
    </StackPanel>

    <!-- Gauge Row -->
    <UniformGrid Grid.Row="1" Columns="3">
      <local:RadialGauge Value="{Binding Temperature}"
                         Min="-40" Max="125" Unit="C"/>
      <local:RadialGauge Value="{Binding Humidity}"
                         Min="0" Max="100" Unit="%RH"/>
      <local:RadialGauge Value="{Binding Pressure}"
                         Min="300" Max="1100" Unit="hPa"/>
    </UniformGrid>

    <!-- Trend Chart -->
    <local:LineChart Grid.Row="2"
                     DataSource="{Binding TrendData}"/>

    <!-- Command Panel -->
    <StackPanel Grid.Row="3" Orientation="Horizontal">
      <Button Content="Start" Command="{Binding StartCommand}"/>
      <Button Content="Stop"  Command="{Binding StopCommand}"/>
      <Button Content="Reset" Command="{Binding ResetCommand}"/>
    </StackPanel>
  </Grid>
</Window>
```

## Step 3: ViewModel Binding Points

The ViewModel structure follows the CommunityToolkit.Mvvm pattern with ObservableProperty.

| Property | Type | Binding Target | Update Rate |
|----------|------|----------------|-------------|
| Temperature | double | RadialGauge.Value | 10 Hz |
| Humidity | double | RadialGauge.Value | 10 Hz |
| Pressure | double | RadialGauge.Value | 10 Hz |
| TrendData | ObservableCollection | LineChart.DataSource | 10 Hz |
| ConnectionStatusBrush | Brush | StatusLed.Fill | On change |
| ConnectionLabel | string | Header TextBlock | On change |
| StartCommand | IRelayCommand | Button.Command | User action |
| StopCommand | IRelayCommand | Button.Command | User action |
| ResetCommand | IRelayCommand | Button.Command | User action |

## Step 4: Design Tokens and Theme

The dark theme template defines consistent visual tokens for the industrial monitoring context.

| Token | Value | Usage |
|-------|-------|-------|
| BackgroundPrimary | #1E1E2E | Window background |
| BackgroundCard | #2A2A3C | Panel/card background |
| TextPrimary | #FFFFFFDE | Primary text |
| TextSecondary | #FFFFFF99 | Secondary labels |
| AccentGreen | #4CAF50 | Normal status, connected |
| AccentYellow | #FFC107 | Warning threshold |
| AccentRed | #F44336 | Error/disconnected |
| GaugeArc | #3F51B5 | Gauge arc background |
| ChartLine | #2196F3 | Trend line color |

ResourceDictionary structure:
```
Themes/
  DarkTheme.xaml        -- Color tokens and base styles
  GaugeStyle.xaml       -- RadialGauge template and format
  ChartStyle.xaml       -- LineChart axes and grid pattern
  ButtonStyle.xaml      -- CommandPanel button format
```

## Summary

- Layout uses Grid-based responsive structure with 4 distinct zones
- Components are encapsulated as UserControls for reuse
- ViewModel bindings use CommunityToolkit.Mvvm pattern (no x:Bind)
- Dark theme design tokens ensure consistent industrial look

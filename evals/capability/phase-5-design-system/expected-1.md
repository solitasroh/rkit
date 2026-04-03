## Step 1: Design Token Definitions

The token layer provides the foundation for consistent theming across all components.
Tokens are defined as StaticResource keys in a ResourceDictionary.

| Token Category | Token Name | Dark Value | Light Value |
|---------------|------------|------------|-------------|
| Background | BgPrimary | #1E1E2E | #FAFAFA |
| Background | BgCard | #2A2A3C | #FFFFFF |
| Background | BgOverlay | #33334D | #F0F0F0 |
| Text | TextPrimary | #FFFFFFDE | #212121DE |
| Text | TextSecondary | #FFFFFF99 | #21212199 |
| Accent | AccentNormal | #4CAF50 | #2E7D32 |
| Accent | AccentWarning | #FFC107 | #F57F17 |
| Accent | AccentError | #F44336 | #C62828 |
| Accent | AccentInfo | #2196F3 | #1565C0 |
| Spacing | SpacingXs | 4 | 4 |
| Spacing | SpacingS | 8 | 8 |
| Spacing | SpacingM | 16 | 16 |
| Spacing | SpacingL | 24 | 24 |
| Typography | FontBody | 14px Segoe UI | 14px Segoe UI |
| Typography | FontCaption | 12px Segoe UI | 12px Segoe UI |
| Typography | FontHeading | 20px Segoe UI SemiBold | 20px Segoe UI SemiBold |

## Step 2: ResourceDictionary Layer Structure

The design system uses a layered ResourceDictionary architecture for clean separation.

```
Components/
  Themes/
    TokensDark.xaml          -- Dark theme token values
    TokensLight.xaml         -- Light theme token values
    ThemeSelector.xaml       -- MergedDictionary switching logic
  Styles/
    RadialGaugeStyle.xaml    -- RadialGauge ControlTemplate
    LineChartStyle.xaml      -- LineChart ControlTemplate
    StatusLedStyle.xaml      -- StatusLed template and states
    CommandButtonStyle.xaml  -- CommandButton template
  Controls/
    RadialGauge.cs           -- Component logic + DependencyProperties
    LineChart.cs             -- Component logic + data bindable API
    StatusLed.cs             -- Component with enum-based state
    CommandButton.cs         -- Component with command interface
```

The layer hierarchy loads in order: Tokens -> Styles -> Controls.
Each layer references only the layer below it, never upward.

```xml
<Application.Resources>
  <ResourceDictionary>
    <ResourceDictionary.MergedDictionaries>
      <ResourceDictionary Source="Themes/TokensDark.xaml"/>
      <ResourceDictionary Source="Styles/RadialGaugeStyle.xaml"/>
      <ResourceDictionary Source="Styles/LineChartStyle.xaml"/>
      <ResourceDictionary Source="Styles/StatusLedStyle.xaml"/>
      <ResourceDictionary Source="Styles/CommandButtonStyle.xaml"/>
    </ResourceDictionary.MergedDictionaries>
  </ResourceDictionary>
</Application.Resources>
```

## Step 3: Component Interface Specifications

Each component exposes a consistent interface through DependencyProperties.

**RadialGauge**
| Property | Type | Default | Description |
|----------|------|---------|-------------|
| Value | double | 0.0 | Current gauge value |
| Minimum | double | 0.0 | Scale minimum |
| Maximum | double | 100.0 | Scale maximum |
| Unit | string | "" | Unit label (C, %RH, hPa) |
| WarningThreshold | double | 80.0 | Yellow zone start |
| ErrorThreshold | double | 95.0 | Red zone start |

**LineChart**
| Property | Type | Default | Description |
|----------|------|---------|-------------|
| ItemsSource | IEnumerable | null | Data point collection |
| TimeWindow | TimeSpan | 5min | Visible time range |
| YAxisMin | double | auto | Y-axis minimum |
| YAxisMax | double | auto | Y-axis maximum |
| SeriesColor | Brush | AccentInfo | Line color |

**StatusLed**
| Property | Type | Default | Description |
|----------|------|---------|-------------|
| Status | LedStatus | Disconnected | Current state enum |
| Label | string | "" | Status text label |

**CommandButton**
| Property | Type | Default | Description |
|----------|------|---------|-------------|
| Command | ICommand | null | Bound command |
| Icon | Geometry | null | Button icon path |
| IsDestructive | bool | false | Red styling for dangerous actions |

## Step 4: Theme Layer Separation

1. Token layer: Pure value definitions, no component references
2. Style layer: ControlTemplate definitions referencing tokens via DynamicResource
3. Component layer: C# logic with DependencyProperty declarations only
4. Application layer: Selects theme by swapping token ResourceDictionary

Theme switching at runtime:
```csharp
public static void SwitchTheme(bool isDark)
{
    var app = Application.Current;
    var mergedDicts = app.Resources.MergedDictionaries;
    mergedDicts.RemoveAt(0); // Remove current token dict
    var uri = isDark
        ? "Themes/TokensDark.xaml"
        : "Themes/TokensLight.xaml";
    mergedDicts.Insert(0, new ResourceDictionary { Source = new Uri(uri, UriKind.Relative) });
}
```

## Summary

- Design tokens provide a single source of truth for all visual properties
- ResourceDictionary layer structure enforces clean separation of concerns
- Component interfaces use DependencyProperties for full XAML binding support
- Theme switching swaps only the token layer, all styles update automatically

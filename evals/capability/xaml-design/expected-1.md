## Step 1: ResourceDictionary Structure

Create the shared resource dictionary file for sensor UI components:

```xml
<ResourceDictionary xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
                    xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
                    xmlns:local="clr-namespace:SensorApp.Converters">

    <!-- Converter instance -->
    <local:TemperatureToColorConverter x:Key="TempToColorConverter" />
</ResourceDictionary>
```

## Step 2: StatusLed Style with DataTriggers

Define the Ellipse style template that changes color based on status:

```xml
<Style x:Key="StatusLedStyle" TargetType="Ellipse">
    <Setter Property="Width" Value="16" />
    <Setter Property="Height" Value="16" />
    <Setter Property="Fill" Value="Gray" />
    <Style.Triggers>
        <DataTrigger Binding="{Binding Status}" Value="Normal">
            <Setter Property="Fill" Value="Green" />
        </DataTrigger>
        <DataTrigger Binding="{Binding Status}" Value="Warning">
            <Setter Property="Fill" Value="Yellow" />
        </DataTrigger>
        <DataTrigger Binding="{Binding Status}" Value="Alarm">
            <Setter Property="Fill" Value="Red" />
        </DataTrigger>
    </Style.Triggers>
</Style>
```

## Step 3: Sensor Item DataTemplate

```xml
<DataTemplate x:Key="SensorItemTemplate">
    <Border BorderBrush="#DDD" BorderThickness="1" CornerRadius="4"
            Padding="12" Margin="4">
        <Grid>
            <Grid.ColumnDefinitions>
                <ColumnDefinition Width="Auto" />
                <ColumnDefinition Width="*" />
                <ColumnDefinition Width="Auto" />
                <ColumnDefinition Width="Auto" />
            </Grid.ColumnDefinitions>

            <Ellipse Grid.Column="0" Style="{StaticResource StatusLedStyle}"
                     Margin="0,0,8,0" />
            <TextBlock Grid.Column="1" Text="{Binding Name}"
                       FontWeight="Bold" VerticalAlignment="Center" />
            <TextBlock Grid.Column="2" VerticalAlignment="Center"
                       Text="{Binding Value, StringFormat='{}{0:F1}'}" />
            <TextBlock Grid.Column="3" Text="{Binding Unit}"
                       Foreground="Gray" Margin="4,0,0,0"
                       VerticalAlignment="Center" />
        </Grid>
    </Border>
</DataTemplate>
```

## Step 4: IValueConverter Implementation

```csharp
public class TemperatureToColorConverter : IValueConverter
{
    public object Convert(object value, Type targetType,
                          object parameter, CultureInfo culture)
    {
        if (value is double temp)
        {
            return temp switch
            {
                < 10.0 => new SolidColorBrush(Colors.CornflowerBlue),
                < 30.0 => new SolidColorBrush(Colors.ForestGreen),
                < 50.0 => new SolidColorBrush(Colors.Orange),
                _      => new SolidColorBrush(Colors.OrangeRed),
            };
        }
        return new SolidColorBrush(Colors.Gray);
    }

    public object ConvertBack(object value, Type targetType,
                               object parameter, CultureInfo culture)
    {
        throw new NotSupportedException();
    }
}
```

## Step 5: Gauge with Converter Binding

```xml
<Border Background="{Binding Temperature,
            Converter={StaticResource TempToColorConverter}}"
        CornerRadius="8" Padding="16">
    <StackPanel>
        <TextBlock Text="Temperature" FontSize="14" Foreground="White" />
        <TextBlock Text="{Binding Temperature, StringFormat='{}{0:F1} C'}"
                   FontSize="32" FontWeight="Bold" Foreground="White" />
    </StackPanel>
</Border>
```

## Design Pattern Summary
- ResourceDictionary provides centralized, reusable format for all sensor styles
- DataTriggers handle status-to-color mapping declaratively in XAML
- IValueConverter transforms numeric values to visual properties
- DataTemplate defines the repeatable structure for sensor list items
- All bindings use `{Binding}` (WPF standard), never `{x:Bind}`

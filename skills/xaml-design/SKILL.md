---
name: xaml-design
classification: capability
deprecation-risk: low
domain: wpf
description: |
  XAML UI 디자인/스타일 가이드. ResourceDictionary, DataTemplate, Converter, Style.
  Triggers: XAML design, style, template, ResourceDictionary, converter
user-invocable: true
allowed-tools: [Read, Write, Edit, Glob, Grep]
pdca-phase: do
---

# XAML Design Guide

## Style Definition
```xml
<Window.Resources>
    <Style x:Key="PrimaryButton" TargetType="Button">
        <Setter Property="Background" Value="#0078D4"/>
        <Setter Property="Foreground" Value="White"/>
        <Setter Property="Padding" Value="16,8"/>
        <Setter Property="FontSize" Value="14"/>
    </Style>
</Window.Resources>
<Button Style="{StaticResource PrimaryButton}" Content="Click Me"/>
```

## DataTemplate
```xml
<DataTemplate DataType="{x:Type local:SensorData}">
    <StackPanel Orientation="Horizontal">
        <TextBlock Text="{Binding Name}" FontWeight="Bold"/>
        <TextBlock Text="{Binding Value, StringFormat='{}{0:F2}'}" Margin="8,0"/>
    </StackPanel>
</DataTemplate>
```

## ResourceDictionary (Separate file)
```xml
<!-- Resources/Styles.xaml -->
<ResourceDictionary xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation">
    <SolidColorBrush x:Key="AccentBrush" Color="#0078D4"/>
</ResourceDictionary>

<!-- App.xaml -->
<Application.Resources>
    <ResourceDictionary>
        <ResourceDictionary.MergedDictionaries>
            <ResourceDictionary Source="Resources/Styles.xaml"/>
        </ResourceDictionary.MergedDictionaries>
    </ResourceDictionary>
</Application.Resources>
```

## IValueConverter
```csharp
public class BoolToVisibilityConverter : IValueConverter
{
    public object Convert(object value, Type t, object p, CultureInfo c) =>
        (bool)value ? Visibility.Visible : Visibility.Collapsed;
    public object ConvertBack(object value, Type t, object p, CultureInfo c) =>
        (Visibility)value == Visibility.Visible;
}
```

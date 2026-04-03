## Step 1: Service Interface Definition

Define the abstraction layer for sensor data access:

```csharp
public interface ISensorService
{
    Task<SensorReading> GetLatestReadingAsync();
    Task<bool> ResetSensorAsync();
    bool IsConnected { get; }
}

public record SensorReading(
    double Temperature,
    double Humidity,
    DateTime Timestamp);
```

## Step 2: ViewModel Class with ObservableObject

The ViewModel follows the CommunityToolkit.Mvvm pattern with source generators:

```csharp
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

public partial class SensorDashboardViewModel : ObservableObject
{
    private readonly ISensorService _sensorService;

    public SensorDashboardViewModel(ISensorService sensorService)
    {
        _sensorService = sensorService;
    }

    [ObservableProperty]
    private double _temperature;

    [ObservableProperty]
    private double _humidity;

    [ObservableProperty]
    private string _connectionStatus = "Disconnected";

    [ObservableProperty]
    private DateTime _lastUpdate;

    [ObservableProperty]
    private bool _isRefreshing;
}
```

## Step 3: RelayCommand Methods

```csharp
public partial class SensorDashboardViewModel
{
    [RelayCommand]
    private async Task RefreshDataAsync()
    {
        if (!_sensorService.IsConnected)
        {
            ConnectionStatus = "Disconnected";
            return;
        }

        IsRefreshing = true;
        try
        {
            var reading = await _sensorService.GetLatestReadingAsync();
            Temperature = reading.Temperature;
            Humidity = reading.Humidity;
            LastUpdate = reading.Timestamp;
            ConnectionStatus = "Connected";
        }
        catch (Exception ex)
        {
            ConnectionStatus = $"Error: {ex.Message}";
        }
        finally
        {
            IsRefreshing = false;
        }
    }

    [RelayCommand]
    private async Task ResetSensorAsync()
    {
        var success = await _sensorService.ResetSensorAsync();
        ConnectionStatus = success ? "Reset OK" : "Reset Failed";
    }
}
```

## Step 4: DI Registration

```csharp
public static class ServiceRegistration
{
    public static IServiceCollection AddSensorServices(
        this IServiceCollection services)
    {
        services.AddSingleton<ISensorService, SerialSensorService>();
        services.AddTransient<SensorDashboardViewModel>();
        return services;
    }
}
```

## Step 5: XAML Data Binding (Binding, not x:Bind)

The View uses standard WPF `{Binding}` format, never `{x:Bind}`:

```xml
<TextBlock Text="{Binding Temperature, StringFormat='{}{0:F1} C'}" />
<TextBlock Text="{Binding Humidity, StringFormat='{}{0:F1} %'}" />
<TextBlock Text="{Binding ConnectionStatus}" />
<Button Command="{Binding RefreshDataCommand}" Content="Refresh" />
<Button Command="{Binding ResetSensorCommand}" Content="Reset" />
```

## MVVM Pattern Compliance
- ViewModel has zero references to System.Windows or UI controls
- All UI state is exposed via [ObservableProperty] with proper structure
- Commands use [RelayCommand] attribute for source-generated ICommand
- DI constructor injection follows the template for testability
- WPF uses `{Binding}` only; `{x:Bind}` is a UWP/WinUI-only feature

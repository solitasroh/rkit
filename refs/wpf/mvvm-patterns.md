# WPF MVVM Patterns Reference

## CommunityToolkit.Mvvm (Recommended)

### ObservableObject + [ObservableProperty]
```csharp
public partial class SensorViewModel : ObservableObject
{
    [ObservableProperty]
    private double _temperature;  // Generates: public double Temperature { get; set; }

    [ObservableProperty]
    private bool _isConnected;    // Generates: public bool IsConnected { get; set; }
}
```

### [RelayCommand]
```csharp
[RelayCommand]
private void Connect() { /* sync */ }

[RelayCommand]
private async Task RefreshAsync() { /* async */ }

[RelayCommand(CanExecute = nameof(CanSend))]
private void Send() { /* with CanExecute */ }
private bool CanSend() => IsConnected;
```

## DI Pattern
```csharp
// App.xaml.cs
public partial class App : Application
{
    public static IServiceProvider Services { get; private set; }

    protected override void OnStartup(StartupEventArgs e)
    {
        Services = new ServiceCollection()
            .AddSingleton<ISerialService, SerialService>()
            .AddSingleton<MainViewModel>()
            .BuildServiceProvider();

        new MainWindow { DataContext = Services.GetRequiredService<MainViewModel>() }.Show();
    }
}
```

## SerialPort (.NET 8)
```csharp
// NuGet: System.IO.Ports (NOT built-in in .NET 8)
using System.IO.Ports;

public class SerialService : ISerialService
{
    private SerialPort _port;

    public void Open(string portName, int baudRate)
    {
        _port = new SerialPort(portName, baudRate, Parity.None, 8, StopBits.One);
        _port.DataReceived += OnDataReceived;
        _port.Open();
    }

    private void OnDataReceived(object sender, SerialDataReceivedEventArgs e)
    {
        var data = _port.ReadExisting();
        DataReceived?.Invoke(data);
    }

    public event Action<string> DataReceived;
}
```

## Key Warnings
- {x:Bind} is UWP/WinUI only — use {Binding} in WPF
- Binding errors are runtime-only (Output window: "Data Error: 40")
- Prism 9.0+ requires commercial license
- .NET 8: TargetFramework must be `net8.0-windows` (not `net8.0`)

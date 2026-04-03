## Step 1: SerialPort Wrapper Service

Define an interface and implementation class for serial port communication.
The service encapsulates all System.IO.Ports usage away from the ViewModel.

```csharp
public interface ISerialService : IDisposable
{
    event EventHandler<SensorData>? DataReceived;
    event EventHandler<string>? ErrorOccurred;
    event EventHandler<bool>? ConnectionChanged;

    bool IsConnected { get; }
    Task ConnectAsync(string portName, int baudRate);
    void Disconnect();
}

public class SensorData
{
    public double Temperature { get; init; }
    public double Humidity { get; init; }
    public double Pressure { get; init; }
    public DateTime Timestamp { get; init; }
}

public class SerialService : ISerialService
{
    private SerialPort? _serialPort;
    private readonly byte[] _rxBuffer = new byte[1024];
    private bool _disposed;

    public event EventHandler<SensorData>? DataReceived;
    public event EventHandler<string>? ErrorOccurred;
    public event EventHandler<bool>? ConnectionChanged;

    public bool IsConnected => _serialPort?.IsOpen ?? false;

    public Task ConnectAsync(string portName, int baudRate)
    {
        _serialPort = new SerialPort(portName, baudRate, Parity.None, 8, StopBits.One);
        _serialPort.DataReceived += OnSerialDataReceived;
        _serialPort.ErrorReceived += OnSerialError;
        _serialPort.Open();
        ConnectionChanged?.Invoke(this, true);
        return Task.CompletedTask;
    }

    private void OnSerialDataReceived(object sender, SerialDataReceivedEventArgs e)
    {
        /* Parse incoming bytes into SensorData and raise event */
        var data = ParseFrame(_rxBuffer);
        if (data != null)
        {
            DataReceived?.Invoke(this, data);
        }
    }

    public void Dispose()
    {
        if (!_disposed)
        {
            _serialPort?.Close();
            _serialPort?.Dispose();
            _disposed = true;
        }
    }
}
```

## Step 2: ViewModel with [ObservableProperty] Binding

The ViewModel uses CommunityToolkit.Mvvm source generators for property notification.
UI-bound properties are decorated with [ObservableProperty].

```csharp
public partial class DashboardViewModel : ObservableObject, IDisposable
{
    private readonly ISerialService _serialService;
    private readonly IDispatcherService _dispatcher;
    private CancellationTokenSource? _reconnectCts;

    [ObservableProperty]
    private double _temperature;

    [ObservableProperty]
    private double _humidity;

    [ObservableProperty]
    private double _pressure;

    [ObservableProperty]
    private bool _isConnected;

    [ObservableProperty]
    private string _statusMessage = "Disconnected";

    public DashboardViewModel(ISerialService serialService, IDispatcherService dispatcher)
    {
        _serialService = serialService;
        _dispatcher = dispatcher;
        _serialService.DataReceived += OnDataReceived;
        _serialService.ConnectionChanged += OnConnectionChanged;
        _serialService.ErrorOccurred += OnError;
    }
}
```

## Step 3: Dispatcher.Invoke for Thread Safety

1. Serial DataReceived fires on a background thread (ThreadPool)
2. ViewModel properties bound to UI must be updated on the UI thread
3. Use an IDispatcherService interface to avoid direct System.Windows dependency

```csharp
public interface IDispatcherService
{
    void Invoke(Action action);
    Task InvokeAsync(Action action);
}

public class WpfDispatcherService : IDispatcherService
{
    public void Invoke(Action action)
    {
        Application.Current.Dispatcher.Invoke(action);
    }

    public Task InvokeAsync(Action action)
    {
        return Application.Current.Dispatcher.InvokeAsync(action).Task;
    }
}

/* In ViewModel: marshal serial data to UI thread */
private void OnDataReceived(object? sender, SensorData data)
{
    _dispatcher.Invoke(() =>
    {
        Temperature = data.Temperature;
        Humidity = data.Humidity;
        Pressure = data.Pressure;
        StatusMessage = $"Last update: {data.Timestamp:HH:mm:ss}";
    });
}
```

## Step 4: Error Detection and Reconnect Handling

1. Subscribe to SerialPort.ErrorReceived and connection loss events
2. On disconnect, start reconnect loop with exponential back-off
3. Back-off intervals: 1s, 2s, 4s, 8s, max 30s between attempts
4. Cancel reconnect on manual disconnect or application shutdown

```csharp
private void OnConnectionChanged(object? sender, bool connected)
{
    _dispatcher.Invoke(() =>
    {
        IsConnected = connected;
        StatusMessage = connected ? "Connected" : "Disconnected - reconnecting...";
    });

    if (!connected)
    {
        StartReconnect();
    }
}

private async void StartReconnect()
{
    _reconnectCts?.Cancel();
    _reconnectCts = new CancellationTokenSource();
    const int MAX_DELAY_MS = 30000;
    int delayMs = 1000;

    while (!_reconnectCts.Token.IsCancellationRequested)
    {
        try
        {
            await Task.Delay(delayMs, _reconnectCts.Token);
            await _serialService.ConnectAsync(_lastPortName, _lastBaudRate);
            return; /* reconnect succeeded */
        }
        catch (OperationCanceledException) { return; }
        catch
        {
            delayMs = Math.Min(delayMs * 2, MAX_DELAY_MS);
        }
    }
}

public void Dispose()
{
    _reconnectCts?.Cancel();
    _reconnectCts?.Dispose();
    _serialService.DataReceived -= OnDataReceived;
    _serialService.Dispose();
}
```

## Step 5: DI Registration

```csharp
public static class ServiceRegistration
{
    public static IServiceCollection AddDashboardServices(this IServiceCollection services)
    {
        services.AddSingleton<ISerialService, SerialService>();
        services.AddSingleton<IDispatcherService, WpfDispatcherService>();
        services.AddTransient<DashboardViewModel>();
        return services;
    }
}
```

## Summary

- SerialPort is wrapped in a service class with clean interface abstraction
- ViewModel uses [ObservableProperty] for automatic INotifyPropertyChanged
- Thread marshaling uses IDispatcherService to keep ViewModel testable
- Reconnect logic uses exponential back-off with cancellation support
- Disposal chain ensures serial resources are released on shutdown

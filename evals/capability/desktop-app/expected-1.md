## Step 1: Project Configuration (.csproj)

The .csproj config uses Microsoft.NET.Sdk with WPF enabled for .NET 8.

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>WinExe</OutputType>
    <TargetFramework>net8.0-windows</TargetFramework>
    <UseWPF>true</UseWPF>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <ApplicationIcon>Assets\app.ico</ApplicationIcon>
  </PropertyGroup>

  <ItemGroup>
    <PackageReference Include="CommunityToolkit.Mvvm" Version="8.2.2" />
    <PackageReference Include="Microsoft.Extensions.DependencyInjection" Version="8.0.0" />
    <PackageReference Include="Microsoft.Extensions.Hosting" Version="8.0.0" />
  </ItemGroup>
</Project>
```

Setup notes:
- `net8.0-windows` is required for WPF (not plain `net8.0`)
- `UseWPF` must be `true` (not `UseWinUI` which is for WinUI3)
- CommunityToolkit.Mvvm provides source generators for [ObservableProperty] and [RelayCommand]

## Step 2: MVVM Folder Structure

```
SensorMonitor/
  App.xaml                    -- Application entry, DI setup
  App.xaml.cs                 -- Host builder and service registration
  Models/
    SensorData.cs             -- Data transfer object for sensor readings
    DeviceInfo.cs             -- MCU device information model
    AppSettings.cs            -- Serializable application config
  ViewModels/
    MainViewModel.cs          -- Dashboard ViewModel (ObservableObject)
    SettingsViewModel.cs      -- Settings page ViewModel
    ViewModelLocator.cs       -- DI-based ViewModel resolution
  Views/
    MainWindow.xaml           -- Dashboard layout with gauges and chart
    SettingsWindow.xaml        -- COM port and display settings
  Services/
    ISerialService.cs         -- Serial communication interface
    SerialService.cs          -- System.IO.Ports implementation
    IDispatcherService.cs     -- UI thread marshaling interface
    WpfDispatcherService.cs   -- WPF Dispatcher implementation
  Components/
    RadialGauge.xaml          -- Custom gauge UserControl
    LineChart.xaml             -- Time-series chart UserControl
    StatusLed.xaml             -- Connection status indicator
  Themes/
    DarkTheme.xaml            -- Dark theme ResourceDictionary
    LightTheme.xaml           -- Light theme ResourceDictionary
```

## Step 3: DI Container Setup

1. Create a HostBuilder in App.xaml.cs for service registration
2. Register services with appropriate lifetimes
3. Resolve ViewModels through the DI container, not manual construction

```csharp
public partial class App : Application
{
    private readonly IHost _host;

    public App()
    {
        _host = Host.CreateDefaultBuilder()
            .ConfigureServices((context, services) =>
            {
                // Services
                services.AddSingleton<ISerialService, SerialService>();
                services.AddSingleton<IDispatcherService, WpfDispatcherService>();

                // ViewModels
                services.AddTransient<MainViewModel>();
                services.AddTransient<SettingsViewModel>();

                // Views
                services.AddTransient<MainWindow>();
            })
            .Build();
    }

    protected override async void OnStartup(StartupEventArgs e)
    {
        await _host.StartAsync();
        var mainWindow = _host.Services.GetRequiredService<MainWindow>();
        mainWindow.Show();
        base.OnStartup(e);
    }

    protected override async void OnExit(ExitEventArgs e)
    {
        await _host.StopAsync();
        _host.Dispose();
        base.OnExit(e);
    }
}
```

## Step 4: SerialPort Service Interface

The interface abstracts serial communication for testability and WinUI3 portability.

```csharp
public interface ISerialService : IDisposable
{
    bool IsConnected { get; }
    string[] GetAvailablePorts();
    Task ConnectAsync(string portName, int baudRate);
    void Disconnect();

    event EventHandler<SensorData>? DataReceived;
    event EventHandler<bool>? ConnectionChanged;
    event EventHandler<string>? ErrorOccurred;
}
```

Key design rules:
- ViewModel depends on ISerialService, never on System.IO.Ports.SerialPort directly
- ViewModel must NOT reference System.Windows.Controls or any UI namespace
- Events use standard .NET event pattern for loose coupling
- Disposal config ensures COM port is released on application shutdown

## Step 5: WinUI3 Migration Compatibility Notes

1. **Binding syntax**: Use `{Binding}` (not `{x:Bind}`) -- `{x:Bind}` is UWP/WinUI only, not available in WPF
2. **Dispatcher**: Abstract via IDispatcherService -- WinUI3 uses DispatcherQueue instead of Dispatcher
3. **ResourceDictionary**: Keep theme structure identical -- WinUI3 uses same XAML ResourceDictionary format
4. **DI container**: Microsoft.Extensions.DependencyInjection works in both WPF and WinUI3
5. **SerialPort**: System.IO.Ports works in both frameworks on .NET 8
6. **Project config change**: Replace `<UseWPF>true</UseWPF>` with `<UseWinUI>true</UseWinUI>` and update TargetFramework setup
7. **Window class**: WinUI3 uses Microsoft.UI.Xaml.Window instead of System.Windows.Window

Migration setup checklist:
- [ ] No x:Bind usage in any XAML file
- [ ] No System.Windows.Controls reference in any ViewModel
- [ ] All UI thread access goes through IDispatcherService
- [ ] All platform-specific code isolated in Services layer

## Summary

- .csproj config uses net8.0-windows with UseWPF and CommunityToolkit.Mvvm
- MVVM folder structure separates Views, ViewModels, Services, and Models
- DI container manages service lifetimes and ViewModel resolution
- SerialPort interface abstraction enables testing and WinUI3 migration
- Seven specific compatibility rules ensure smooth WinUI3 transition

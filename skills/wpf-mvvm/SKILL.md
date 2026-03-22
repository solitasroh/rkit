---
name: wpf-mvvm
classification: capability
deprecation-risk: low
domain: wpf
description: |
  WPF MVVM 아키텍처 가이드. CommunityToolkit.Mvvm, DI, 네비게이션 패턴.
  Triggers: WPF, MVVM, ViewModel, CommunityToolkit, ObservableObject, RelayCommand
user-invocable: true
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep]
imports:
  - ${PLUGIN_ROOT}/refs/wpf/mvvm-patterns.md
pdca-phase: do
---

# WPF MVVM Guide

## Project Setup (.NET 8)
```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>WinExe</OutputType>
    <TargetFramework>net8.0-windows</TargetFramework>
    <UseWPF>true</UseWPF>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="CommunityToolkit.Mvvm" Version="8.*" />
    <PackageReference Include="Microsoft.Extensions.DependencyInjection" Version="8.*" />
  </ItemGroup>
</Project>
```

## ViewModel Pattern (CommunityToolkit.Mvvm)
```csharp
public partial class MainViewModel : ObservableObject
{
    [ObservableProperty]    // Generates public 'Name' property
    private string _name = "";

    [ObservableProperty]
    private int _count;

    [RelayCommand]          // Generates 'IncrementCommand' ICommand
    private void Increment() => Count++;

    [RelayCommand]
    private async Task LoadDataAsync()
    {
        Name = await _dataService.GetNameAsync();
    }

    private readonly IDataService _dataService;
    public MainViewModel(IDataService dataService) => _dataService = dataService;
}
```

## DI Setup (App.xaml.cs)
```csharp
public partial class App : Application
{
    private readonly IServiceProvider _services;

    public App()
    {
        _services = new ServiceCollection()
            .AddSingleton<MainViewModel>()
            .AddSingleton<IDataService, DataService>()
            .BuildServiceProvider();
    }

    protected override void OnStartup(StartupEventArgs e)
    {
        var vm = _services.GetRequiredService<MainViewModel>();
        new MainWindow { DataContext = vm }.Show();
    }
}
```

## View Binding
```xml
<Window DataContext="{Binding}">
    <StackPanel>
        <TextBox Text="{Binding Name, Mode=TwoWay, UpdateSourceTrigger=PropertyChanged}" />
        <TextBlock Text="{Binding Count}" />
        <Button Content="Increment" Command="{Binding IncrementCommand}" />
    </StackPanel>
</Window>
```

## Key Rules
- NO `{x:Bind}` (UWP/WinUI only)
- ViewModel must NOT reference System.Windows.Controls
- Prism 9.0+ is commercial — use CommunityToolkit.Mvvm for new projects
- Binding errors are runtime-only (check Output window for "Data Error: 40")

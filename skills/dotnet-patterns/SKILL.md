---
name: dotnet-patterns
classification: capability
deprecation-risk: low
domain: wpf
description: |
  .NET DI/패턴/테스트 가이드. Microsoft.Extensions.DI, xUnit, async/await 패턴.
  Triggers: .NET, C#, DI, dependency injection, xUnit, async, pattern
user-invocable: true
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep]
pdca-phase: do
---

# .NET Patterns Guide

## Dependency Injection
```csharp
var services = new ServiceCollection()
    .AddSingleton<ISerialService, SerialService>()
    .AddTransient<MainViewModel>()
    .BuildServiceProvider();
```

## xUnit Testing (ViewModel)
```csharp
public class MainViewModelTests
{
    [Fact]
    public void Increment_ShouldIncreaseCount()
    {
        var vm = new MainViewModel(Mock.Of<IDataService>());
        vm.IncrementCommand.Execute(null);
        Assert.Equal(1, vm.Count);
    }
}
```
ViewModel tests run WITHOUT WPF runtime (key MVVM benefit).

## Async Pattern
```csharp
[RelayCommand]
private async Task LoadAsync()
{
    IsLoading = true;
    try { Data = await _service.GetDataAsync(); }
    finally { IsLoading = false; }
}
```

## Configuration
- .NET 8 WPF: `appsettings.json` (add Microsoft.Extensions.Configuration manually)
- .NET Framework: `App.config` (ConfigurationManager, built-in)

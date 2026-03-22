# {feature} MVVM Architecture Specification

## 1. Project Structure
```
{project}/
├── Views/           # .xaml + .xaml.cs (code-behind minimal)
├── ViewModels/      # ObservableObject derivatives
├── Models/          # Data classes
├── Services/        # Business logic interfaces + implementations
├── Converters/      # IValueConverter implementations
├── Resources/       # ResourceDictionary files
└── App.xaml         # DI container setup
```

## 2. ViewModel Map
| ViewModel | View | Services |
|-----------|------|----------|
| {vm} | {view}.xaml | {services} |

## 3. Service Interfaces
| Interface | Implementation | Lifetime |
|-----------|---------------|:--------:|
| I{Service} | {Service} | Singleton/Transient |

## 4. DI Registration
```csharp
services.AddSingleton<I{Service}, {Service}>();
services.AddTransient<{ViewModel}>();
```

## 5. MVVM Checklist
- [ ] All ViewModels inherit ObservableObject
- [ ] No System.Windows.Controls reference in ViewModels
- [ ] Commands use [RelayCommand] attribute
- [ ] DI via constructor injection
- [ ] SerialPort via System.IO.Ports NuGet (if needed)

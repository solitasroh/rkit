# Modern C# Code Structure Quality Guide

Domain-agnostic rules for LLM-generated C# code. Targets C# 12 / .NET 8+.

---

## MVVM Boundaries

View = pure presentation. ViewModel = state + commands. Model = domain logic.
ViewModel must never reference `System.Windows` types.

```csharp
// Bad — ViewModel coupled to View
public class OrderVM { private readonly OrderWindow _w; public void Save() { _w.Close(); } }

// Good — ViewModel exposes intent, View reacts
public partial class OrderVM : ObservableObject
{
    public event Action? CloseRequested;
    [RelayCommand]
    private void Save() { _repo.Save(_order); CloseRequested?.Invoke(); }
}
```

## Dependency Injection

Constructor injection only. No `new` inside classes. No Service Locator outside composition root.

```csharp
// Bad
public class CustomerVM { private readonly CustomerService _svc = new(); }
// Good — C# 12 primary constructor
public class CustomerVM(ICustomerService svc) : ObservableObject
{
    [RelayCommand] private async Task LoadAsync() => Customers = await svc.GetAllAsync();
}
```

## INotifyPropertyChanged & Commands

Use CommunityToolkit.Mvvm `[ObservableProperty]` and `[RelayCommand]`. Always implement `CanExecute`.

```csharp
// Bad — manual boilerplate, always-enabled command
private string _name = "";
public string Name { get => _name; set { _name = value; OnPropertyChanged(); } }
public ICommand SaveCmd => new RelayCommand(() => Save());

// Good — source-generated, guarded command
[ObservableProperty] [NotifyPropertyChangedFor(nameof(FullName))]
private string _name = "";

[RelayCommand(CanExecute = nameof(CanSave))]
private async Task SaveAsync() => await _repo.SaveAsync(_order);
private bool CanSave => _order is { IsValid: true } && !IsBusy;
```

## Async / Await

`async void` only for event handlers. Never `.Result`/`.Wait()`. `ConfigureAwait(false)` in libraries.

```csharp
// Bad — deadlock
public void Load() { var data = _svc.GetDataAsync().Result; }
// Good
public async Task LoadAsync()
{
    var data = await _svc.GetDataAsync();
    Items = new ObservableCollection<Item>(data);
}
```

## Collections & Interfaces

`ObservableCollection<T>` for bound lists — replace entire collection for bulk updates.
Every external dependency behind an interface: `IRepository<T>`, `IFileService`,
`IDialogService`, `INavigationService`, `TimeProvider` (.NET 8 built-in).

```csharp
// Bad — fires N events
foreach (var item in items) Collection.Add(item);
// Good — single notification
Items = new ObservableCollection<Item>(await _svc.GetAllAsync());
```

---

## Modern C# 12 / .NET 8

### Records & primary constructors

```csharp
// Bad — equality boilerplate class
public class Money { public decimal Amount { get; } public string Currency { get; }
    public override bool Equals(object? obj) => /* 5 more lines */ }
// Good — record
public record Money(decimal Amount, string Currency);

// Bad — field + constructor ceremony
public class OrderService { private readonly IOrderRepository _r;
    public OrderService(IOrderRepository r) { _r = r; } }
// Good — primary constructor
public class OrderService(IOrderRepository repo, ILogger<OrderService> logger) : IOrderService
{
    public async Task<Order?> GetAsync(int id) => await repo.FindAsync(id);
}
```

### Pattern matching & switch expressions

```csharp
// Bad — nested if/else
if (shape is Circle c) return Math.PI * c.Radius * c.Radius;
else if (shape is Rectangle r) return r.Width * r.Height;
// Good — exhaustive switch expression
double area = shape switch
{
    Circle c => Math.PI * c.Radius * c.Radius, Rectangle r => r.Width * r.Height,
    _ => throw new ArgumentOutOfRangeException(nameof(shape))
};
```

### Collection expressions, raw strings, required members

```csharp
// Bad
List<int> ids = new List<int> { 1, 2, 3 };
string json = "{\n  \"name\": \"test\"\n}";
// Good
List<int> ids = [1, 2, 3];
string json = """{ "name": "test" }""";
public class Config
{
    public required string ConnectionString { get; init; }
    public required int MaxRetries { get; init; }
}
```

---

## Clean Architecture Layers

### Domain — entities, value objects, domain events (zero dependencies)

```csharp
// Bad — anemic entity
public class Order { public string Status { get; set; } = ""; }
// Good — rich domain
public class Order : Entity
{
    public OrderStatus Status { get; private set; } = OrderStatus.Draft;
    public void Confirm()
    {
        if (Status != OrderStatus.Draft) throw new DomainException("Only draft orders");
        Status = OrderStatus.Confirmed;
        AddDomainEvent(new OrderConfirmedEvent(Id));
    }
}
```

### Application — use cases via MediatR handlers

```csharp
// Bad — logic in controller
app.MapPost("/orders/{id}/confirm", async (int id, AppDbContext db) =>
    { var o = await db.Orders.FindAsync(id); o!.Status = "Confirmed"; await db.SaveChangesAsync(); });
// Good — handler encapsulates use case
public record ConfirmOrderCommand(int OrderId) : IRequest<ErrorOr<OrderDto>>;
public class ConfirmOrderHandler(IOrderRepository repo, IUnitOfWork uow)
    : IRequestHandler<ConfirmOrderCommand, ErrorOr<OrderDto>>
{
    public async Task<ErrorOr<OrderDto>> Handle(ConfirmOrderCommand cmd, CancellationToken ct)
    {
        var order = await repo.GetByIdAsync(cmd.OrderId, ct);
        if (order is null) return Error.NotFound("Order.NotFound");
        order.Confirm();
        await uow.SaveChangesAsync(ct);
        return order.ToDto();
    }
}
```

### Infrastructure & DependencyInjection.cs per layer

```csharp
// Bad — DbContext in application layer
public class OrderHandler { private readonly AppDbContext _db; }
// Good — repository in infra, wired via DI extension
public class OrderRepository(AppDbContext db) : IOrderRepository
{
    public async Task<Order?> GetByIdAsync(int id, CancellationToken ct)
        => await db.Orders.Include(o => o.Items).FirstOrDefaultAsync(o => o.Id == id, ct);
}
// Each layer exposes: services.AddDomain() / AddApplication() / AddInfrastructure(config)
public static class DependencyInjection
{
    public static IServiceCollection AddInfrastructure(this IServiceCollection svc, IConfiguration cfg)
    {
        svc.AddDbContext<AppDbContext>(o => o.UseNpgsql(cfg.GetConnectionString("Default")));
        svc.AddScoped<IOrderRepository, OrderRepository>();
        return svc;
    }
}
```

---

## Error Handling

### Result / ErrorOr pattern — no exceptions for control flow

```csharp
// Bad — throwing for expected cases
public Order GetOrder(int id) =>
    _db.Orders.Find(id) ?? throw new NotFoundException($"Order {id}");
// Good — errors as values
public async Task<ErrorOr<OrderDto>> GetOrderAsync(int id)
{
    var order = await _repo.GetByIdAsync(id);
    return order is null ? Error.NotFound("Order.NotFound") : order.ToDto();
}
```

### FluentValidation + MediatR pipeline

```csharp
// Bad — manual validation in handler
if (string.IsNullOrEmpty(cmd.Name)) return Error.Validation("Name required");
// Good — declarative validation via pipeline behavior
public class CreateOrderValidator : AbstractValidator<CreateOrderCommand>
{
    public CreateOrderValidator()
    {
        RuleFor(x => x.Name).NotEmpty().MaximumLength(200);
        RuleFor(x => x.Quantity).GreaterThan(0);
    }
}
```

---

## LINQ & Expression Patterns

**Expression-bodied members for single-expression methods:**
```csharp
// Bad — block body for trivial methods
public string FullName { get { return $"{FirstName} {LastName}"; } }
public override string ToString() { return $"Order #{Id}"; }

// Good — expression body
public string FullName => $"{FirstName} {LastName}";
public override string ToString() => $"Order #{Id}";
```

**LINQ for declarative data transformation:**
```csharp
// Bad — imperative loop
var activeNames = new List<string>();
foreach (var u in users)
    if (u.IsActive && u.Age >= 18)
        activeNames.Add(u.Name.ToUpper());

// Good — LINQ pipeline
var activeNames = users
    .Where(u => u.IsActive && u.Age >= 18)
    .Select(u => u.Name.ToUpper())
    .ToList();
```

**Pattern matching in LINQ:**
```csharp
// Filter + cast in one step
var validOrders = items
    .OfType<Order>()
    .Where(o => o is { Status: OrderStatus.Confirmed, Total: > 0 })
    .Select(o => o.ToDto());
```

## Lambda & Delegate Patterns

**Lambda as strategy injection:**
```csharp
// Bad — interface + class for one-shot behavior
interface ISortStrategy { IEnumerable<T> Sort<T>(IEnumerable<T> items); }
class ByNameStrategy : ISortStrategy { /* ... */ }

// Good — Func<T> as lightweight strategy
public class DataGrid<T>(Func<IEnumerable<T>, IEnumerable<T>>? sortStrategy = null)
{
    public IEnumerable<T> GetSorted(IEnumerable<T> items)
        => sortStrategy?.Invoke(items) ?? items;
}
// Usage
var grid = new DataGrid<User>(users => users.OrderBy(u => u.Name));
```

**Local functions over private helper methods (when used once):**
```csharp
// Good — local function keeps logic close to usage
public async Task<ErrorOr<Report>> GenerateReportAsync(int year)
{
    var data = await _repo.GetDataAsync(year);
    if (data.Count == 0) return Error.NotFound("No data");

    return BuildReport(data);

    // Local function — not polluting class scope
    static Report BuildReport(List<DataPoint> points)
    {
        var summary = points.GroupBy(p => p.Category)
            .Select(g => new Section(g.Key, g.Average(p => p.Value)));
        return new Report(summary);
    }
}
```

**Event handling with lambda (avoid verbose handlers):**
```csharp
// Bad — separate named handler for trivial logic
button.Click += Button_Click;
private void Button_Click(object s, EventArgs e) { _vm.SaveCommand.Execute(null); }

// Good — inline lambda
button.Click += (_, _) => _vm.SaveCommand.Execute(null);
```

## Advanced Pattern Matching

**Exhaustive switch with discriminated union (record hierarchy):**
```csharp
// Define closed hierarchy
public abstract record PaymentResult;
public record PaymentSuccess(string TransactionId) : PaymentResult;
public record PaymentDeclined(string Reason) : PaymentResult;
public record PaymentError(Exception Ex) : PaymentResult;

// Exhaustive handling — compiler warns if case missed
public string Describe(PaymentResult result) => result switch
{
    PaymentSuccess s => $"Paid: {s.TransactionId}",
    PaymentDeclined d => $"Declined: {d.Reason}",
    PaymentError e => $"Error: {e.Ex.Message}",
    _ => throw new UnreachableException()
};
```

**Property pattern + relational pattern:**
```csharp
public decimal CalculateDiscount(Order order) => order switch
{
    { Total: > 1000, Customer.IsPremium: true } => order.Total * 0.2m,
    { Total: > 500 } => order.Total * 0.1m,
    { Items.Count: > 10 } => order.Total * 0.05m,
    _ => 0m
};
```

## DDD Building Blocks

**Value Object with record:**
```csharp
// Immutable, equality by value, self-validating
public record Email
{
    public string Value { get; }
    public Email(string value)
    {
        if (!value.Contains('@')) throw new DomainException("Invalid email");
        Value = value;
    }
}
```

**Aggregate Root — encapsulated collection + domain events (eShop pattern):**
```csharp
public class Order : Entity, IAggregateRoot
{
    public OrderStatus Status { get; private set; } = OrderStatus.Draft;
    private readonly List<OrderItem> _items = [];
    public IReadOnlyCollection<OrderItem> Items => _items.AsReadOnly();

    public void AddItem(Product product, int quantity)
    {
        if (Status != OrderStatus.Draft)
            throw new DomainException("Cannot modify confirmed order");
        _items.Add(new OrderItem(product, quantity));
    }

    public void Confirm()
    {
        if (_items.Count == 0) throw new DomainException("Empty order");
        Status = OrderStatus.Confirmed;
        AddDomainEvent(new OrderConfirmedEvent(Id));
    }
}
// Key: private set, private collection, events on state transition
```

**Smart Enum (type-safe, behavior-rich):**
```csharp
// Bad — string/int constants
public const string StatusDraft = "draft";
public const string StatusConfirmed = "confirmed";

// Good — smart enum with behavior
public abstract record OrderStatus(string Name)
{
    public static readonly OrderStatus Draft = new DraftStatus();
    public static readonly OrderStatus Confirmed = new ConfirmedStatus();

    public abstract bool CanTransitionTo(OrderStatus next);

    private record DraftStatus() : OrderStatus("Draft")
    {
        public override bool CanTransitionTo(OrderStatus next) => next == Confirmed;
    }
    private record ConfirmedStatus() : OrderStatus("Confirmed")
    {
        public override bool CanTransitionTo(OrderStatus next) => false;
    }
}
```

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Public member | PascalCase | `OrderStatus`, `GetByIdAsync` |
| Private field | _camelCase | `_orderRepository` |
| Interface | I prefix | `IOrderService` |
| Async method | Async suffix | `SaveAsync`, `LoadDataAsync` |
| Suffixes | -Service, -Repository, -Handler, -Factory, -Validator | `OrderService` |

```csharp
// Bad
public class orderSvc { private IOrderRepository repo; public void save() { } }
// Good
public class OrderService(IOrderRepository _orderRepository) : IOrderService
{
    public async Task SaveAsync(Order order) => await _orderRepository.UpdateAsync(order);
}
```

---

## Reference Repo Patterns (Pre-extracted)

> When designing C# classes/modules, apply these patterns from real-world production repos.

### jasontaylordev/CleanArchitecture (20k stars) — 4-Layer Structure

**Pattern 1: DependencyInjection.cs per layer**
```csharp
// Each layer has its own registration extension method
// Domain/DependencyInjection.cs — usually empty (pure domain)
// Application/DependencyInjection.cs
public static class DependencyInjection
{
    public static IServiceCollection AddApplication(this IServiceCollection services)
    {
        services.AddMediatR(cfg => cfg.RegisterServicesFromAssembly(typeof(DependencyInjection).Assembly));
        services.AddValidatorsFromAssembly(typeof(DependencyInjection).Assembly);
        services.AddTransient(typeof(IPipelineBehavior<,>), typeof(ValidationBehavior<,>));
        return services;
    }
}
// Program.cs — clean composition root
builder.Services.AddApplication().AddInfrastructure(builder.Configuration);
```

**Pattern 2: MediatR pipeline behaviors (cross-cutting concerns)**
```csharp
// Validation runs automatically before every handler
public class ValidationBehavior<TRequest, TResponse>(IEnumerable<IValidator<TRequest>> validators)
    : IPipelineBehavior<TRequest, TResponse> where TRequest : notnull
{
    public async Task<TResponse> Handle(TRequest request, RequestHandlerDelegate<TResponse> next, CancellationToken ct)
    {
        var context = new ValidationContext<TRequest>(request);
        var failures = validators.Select(v => v.Validate(context))
            .SelectMany(r => r.Errors).Where(f => f is not null).ToList();
        if (failures.Count != 0) throw new ValidationException(failures);
        return await next();
    }
}
```

**Apply this**: Every new layer → add `DependencyInjection.cs`. Cross-cutting (validation, logging, auth) → MediatR pipeline behavior, not manual checks in handlers.

---

### amantinband/error-or (2k stars) — Functional Error Handling

**Pattern: ErrorOr<T> chaining with Then/Match**
```csharp
// Chain operations — error short-circuits automatically
public async Task<ErrorOr<OrderDto>> CreateOrderAsync(CreateOrderCommand cmd)
{
    return await ValidateCommand(cmd)         // ErrorOr<ValidatedCmd>
        .ThenAsync(v => _repo.CreateAsync(v)) // ErrorOr<Order>
        .Then(order => order.ToDto());         // ErrorOr<OrderDto>
}

// Terminal — handle success or error
var result = await CreateOrderAsync(cmd);
return result.Match(
    onValue: dto => Results.Created($"/orders/{dto.Id}", dto),
    onFirstError: error => error.Type switch
    {
        ErrorType.NotFound => Results.NotFound(error.Description),
        ErrorType.Validation => Results.BadRequest(error.Description),
        _ => Results.Problem(error.Description)
    }
);
```

**Apply this**: Return `ErrorOr<T>` from use cases, not exceptions. Chain with `.Then()`. Map to HTTP responses in the controller layer with `.Match()`.

---

### dotnet/eShop (10k stars) — Production DDD

**Pattern 1: Aggregate root with encapsulated collection**
```csharp
public class Order : Entity, IAggregateRoot
{
    // Private collection — external code cannot modify directly
    private readonly List<OrderItem> _orderItems;
    public IReadOnlyCollection<OrderItem> OrderItems => _orderItems.AsReadOnly();

    // State transitions raise domain events
    public void SetPaidStatus()
    {
        if (OrderStatus != OrderStatus.Validated)
            StatusChangeException(OrderStatus.Paid);
        OrderStatus = OrderStatus.Paid;
        AddDomainEvent(new OrderStatusChangedToPaidDomainEvent(Id, _orderItems));
    }
}
```

**Pattern 2: Domain events dispatched after SaveChanges**
```csharp
// Events collected during domain operations, dispatched after persistence
public override async Task<int> SaveChangesAsync(CancellationToken ct = default)
{
    var result = await base.SaveChangesAsync(ct);
    await DispatchDomainEventsAsync();  // publish after save succeeds
    return result;
}
```

**Apply this**: Collections always `private List<T>` + `IReadOnlyCollection<T>`. State changes via methods (not setters). Domain events after save, not during.

---

### CommunityToolkit/MVVM-Samples (1.4k stars) — MVVM Patterns

**Pattern: Source-generated MVVM with zero boilerplate**
```csharp
public partial class MainViewModel : ObservableObject
{
    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(FullName))]
    [NotifyCanExecuteChangedFor(nameof(SaveCommand))]
    private string _firstName = "";

    public string FullName => $"{FirstName} {LastName}";

    [RelayCommand(CanExecute = nameof(CanSave))]
    private async Task SaveAsync() { /* ... */ }
    private bool CanSave => !string.IsNullOrEmpty(FirstName);
}
```

**Apply this**: Always use `[ObservableProperty]` over manual properties. Always use `[RelayCommand(CanExecute)]` — commands without CanExecute are incomplete.

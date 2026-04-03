# Modern C++ Structure Rules

Rules for generating/reviewing C++ code. Target C++17+.
C-style idioms and C++03 patterns are defects unless documented.

---

## Resource Management — RAII

Every resource is managed by an object whose destructor releases it.
```cpp
// Bad — manual lifetime, exception-unsafe
auto* conn = new Connection(addr);
conn->open(); conn->close(); delete conn;

// Good — RAII, exception-safe
auto conn = std::make_unique<Connection>(addr);
conn->open(); // destructor handles cleanup on any exit path
```
- `unique_ptr` for sole ownership. `shared_ptr` only when genuinely shared.
- `scoped_lock` for mutexes. Manual `lock()`/`unlock()` is forbidden.
- Raw `new`/`delete` forbidden. Use `make_unique`/`make_shared`.

## Ownership in Signatures

| Signature | Meaning |
|-----------|---------|
| `void f(const Widget& w)` | Observes, does not own |
| `void f(Widget& w)` | Modifies, does not own |
| `void f(std::unique_ptr<Widget> w)` | Takes sole ownership |
| `Widget* f()` | Observer only — caller must not delete |

## Type Safety
```cpp
// Bad
#define MAX_RETRIES 3
enum Color { RED, GREEN, BLUE };
auto x = (int)some_float;

// Good
constexpr int max_retries = 3;
enum class Color { Red, Green, Blue };
auto x = static_cast<int>(some_float);
```
`enum class` over `enum`. `constexpr` over `#define`. `static_assert` for compile-time checks. `std::variant` over `void*`.

## Containers and Algorithms
```cpp
// Bad — raw loop with index
for (size_t i = 0; i < items.size(); ++i)
    if (items[i].active) result.push_back(items[i].name);

// Good — ranges pipeline
std::ranges::copy(items | std::views::filter(&Item::active)
                        | std::views::transform(&Item::name),
                  std::back_inserter(result));
```
`std::array` for fixed-size, `std::vector` for dynamic. `std::string_view` for non-owning strings. Prefer `<algorithm>` and `<ranges>` over hand-rolled loops.

## Move Semantics

- Rule of Zero: no resource → declare no special members.
- Rule of Five: define destructor → define or delete all five.
- Never `std::move` in a `return` — it prevents NRVO.

## Lambda Patterns

**Callback with template (zero-overhead) vs std::function (type-erased):**
```cpp
// Bad — always using std::function (heap alloc, indirection)
void forEach(const std::vector<int>& v, std::function<void(int)> fn);

// Good — template for hot path (inlined, zero overhead)
template <typename F>
void forEach(const std::vector<int>& v, F&& fn) {
    for (auto x : v) fn(x);
}
// Use std::function only when you need to STORE the callable (member variable, container)
```

**IILE (Immediately Invoked Lambda) for complex const init:**
```cpp
// Bad — mutable temp variable
std::string msg;
if (error) msg = "failed: " + reason;
else msg = "ok";

// Good — const via IILE
const auto msg = [&] {
    if (error) return "failed: " + reason;
    return std::string("ok");
}();
```

**Generic lambda (auto params) for algorithm predicates:**
```cpp
// Bad — explicit type
std::sort(v.begin(), v.end(), [](const Widget& a, const Widget& b) { return a.name < b.name; });

// Good — generic, reusable
auto byName = [](const auto& a, const auto& b) { return a.name < b.name; };
std::ranges::sort(widgets, byName);
std::ranges::sort(employees, byName);  // works for any type with .name
```

**Move capture for non-copyable objects:**
```cpp
auto ptr = std::make_unique<Config>(load());
// Bad — won't compile, unique_ptr is non-copyable
auto fn = [ptr] { use(*ptr); };

// Good — move into lambda
auto fn = [ptr = std::move(ptr)] { use(*ptr); };
```

**Lambda capture rules:**
- Local scope (passed to algorithm): capture by `[&]` reference — safe, no dangling
- Stored / returned / threaded: capture by `[=]` value or move — avoids dangling
- Never `[=]` when capturing `this` — use `[*this]` for value copy of the object

## Error Handling
```cpp
// Bad — silent swallow
try { parse(input); } catch (...) {}

// Good — typed error propagation
std::expected<Config, ParseError> parse(std::string_view input);
```

| Approach | Use when |
|----------|----------|
| Exceptions | Rare failures, recovery at higher layer |
| `std::optional<T>` | "No value" is normal |
| `std::expected<T,E>` | Caller needs failure reason |

## Templates
```cpp
// Bad — undocumented requirements
template <typename T> void serialize(const T& obj) { obj.to_json(); }

// Good — concept-constrained
template <typename T>
concept Serializable = requires(const T& t) { { t.to_json() } -> std::convertible_to<std::string>; };
template <Serializable T> void serialize(const T& obj) { /* ... */ }
```

## Headers
- IWYU. No transitive include reliance. Forward-declare when possible.
- `#pragma once`. Order: standard -> third-party -> project.

---

## Modern C++17/20 Idioms

**Structured bindings:**
```cpp
// Bad
auto it = config.find("timeout");
if (it != config.end()) use(it->second);
// Good
if (auto [it, inserted] = config.try_emplace("timeout", 30); !inserted)
    use(it->second);
```

**std::optional** for nullable returns:
```cpp
// Bad — returns -1 on miss
int find_index(const std::vector<int>& v, int target);
// Good
std::optional<size_t> find_index(const std::vector<int>& v, int target);
```

**if constexpr:**
```cpp
// Bad — may not compile for non-arithmetic T
template <typename T> std::string to_str(const T& v) {
    if (std::is_arithmetic_v<T>) return std::to_string(v);
}
// Good
template <typename T> std::string to_str(const T& v) {
    if constexpr (std::is_arithmetic_v<T>) return std::to_string(v);
    else return v.serialize();
}
```

**std::span** for non-owning views:
```cpp
// Bad                                  // Good
void process(const int* data, size_t n); void process(std::span<const int> data);
```

**std::format:**
```cpp
// Bad
char buf[128]; snprintf(buf, sizeof(buf), "user=%s count=%d", name, n);
// Good
auto msg = std::format("user={} count={}", name, n);
```

---

## Project Structure
```
project/
  CMakeLists.txt        # project(), add_subdirectory()
  src/                  # implementation files
  include/mylib/        # public API headers
  tests/                # test executables
  lib/                  # vendored dependencies
```
```cmake
# Bad — global paths leak to all targets
include_directories(${CMAKE_SOURCE_DIR}/include)
link_libraries(pthread)

# Good — target-scoped
target_include_directories(mylib PUBLIC include PRIVATE src)
target_link_libraries(mylib PRIVATE Threads::Threads)
```
Public headers under `include/project_name/`. Tests link the library target.

---

## Design Patterns in Modern C++

**Strategy with std::function** (vs virtual hierarchy):
```cpp
// Bad — class hierarchy for one behavior
class Compressor { public: virtual std::vector<uint8_t> compress(std::span<const uint8_t>) = 0; };
// Good — callable strategy
class Archiver {
    std::function<std::vector<uint8_t>(std::span<const uint8_t>)> compress_;
public:
    explicit Archiver(decltype(compress_) fn) : compress_(std::move(fn)) {}
};
```

**CRTP** (zero-overhead static polymorphism):
```cpp
template <typename Derived>
struct Serializer {
    std::string serialize() { return static_cast<Derived*>(this)->do_serialize(); }
};
struct JsonSerializer : Serializer<JsonSerializer> {
    std::string do_serialize() { return "{}"; }
};
```

**RAII wrapper for C APIs:**
```cpp
// Bad — forgot fclose on early return
FILE* f = fopen("data.bin", "rb");
// Good
auto f = std::unique_ptr<FILE, decltype(&fclose)>(fopen("data.bin", "rb"), &fclose);
```

**Builder with method chaining:**
```cpp
class QueryBuilder {
    std::string table_, where_;
public:
    QueryBuilder& from(std::string t) { table_ = std::move(t); return *this; }
    QueryBuilder& where(std::string w) { where_ = std::move(w); return *this; }
    std::string build() const { return std::format("SELECT * FROM {} WHERE {}", table_, where_); }
};
auto q = QueryBuilder{}.from("users").where("active=1").build();
```

**Visitor with std::variant + std::visit (replace inheritance hierarchies):**
```cpp
// Bad — virtual inheritance for closed set of types
class Shape { public: virtual double area() = 0; };
class Circle : public Shape { /* ... */ };
class Rect : public Shape { /* ... */ };

// Good — variant + visit (value semantics, no heap, no vtable)
using Shape = std::variant<Circle, Rect, Triangle>;

// Overload pattern (C++17) — combine multiple lambdas into one visitor
template <class... Ts> struct overload : Ts... { using Ts::operator()...; };

double area(const Shape& s) {
    return std::visit(overload{
        [](const Circle& c)   { return std::numbers::pi * c.r * c.r; },
        [](const Rect& r)     { return r.w * r.h; },
        [](const Triangle& t) { return 0.5 * t.base * t.height; },
    }, s);
}
// Adding a new type to variant → compiler forces all visitors to handle it
```

**Type Erasure (value-semantic polymorphism without inheritance):**
```cpp
// Concept: hide the concrete type behind a uniform interface
// std::function is the canonical example — stores any callable
// Build your own for domain-specific needs:
class Drawable {
    struct Concept {
        virtual ~Concept() = default;
        virtual void draw() const = 0;
        virtual std::unique_ptr<Concept> clone() const = 0;
    };
    template <typename T>
    struct Model : Concept {
        T obj_;
        explicit Model(T obj) : obj_(std::move(obj)) {}
        void draw() const override { obj_.draw(); }
        std::unique_ptr<Concept> clone() const override {
            return std::make_unique<Model>(*this);
        }
    };
    std::unique_ptr<Concept> pimpl_;
public:
    template <typename T>
    Drawable(T obj) : pimpl_(std::make_unique<Model<T>>(std::move(obj))) {}
    void draw() const { pimpl_->draw(); }
};
// Any type with a draw() method works — no base class needed
```

**Policy-Based Design (compile-time strategy injection):**
```cpp
// Bad — runtime strategy with virtual
class Logger { virtual void write(std::string_view) = 0; };

// Good — policy template (zero overhead, resolved at compile time)
template <typename OutputPolicy, typename FormatPolicy>
class Logger : private OutputPolicy, private FormatPolicy {
public:
    template <typename... Args>
    void log(std::format_string<Args...> fmt, Args&&... args) {
        auto msg = FormatPolicy::format(fmt, std::forward<Args>(args)...);
        OutputPolicy::write(msg);
    }
};

struct ConsoleOutput { static void write(std::string_view msg) { std::cout << msg << '\n'; } };
struct TimestampFormat {
    template <typename... Args>
    static std::string format(std::format_string<Args...> fmt, Args&&... args) {
        return std::format("[{}] {}", /* now */, std::format(fmt, std::forward<Args>(args)...));
    }
};
using AppLogger = Logger<ConsoleOutput, TimestampFormat>;
```

**Deducing This (C++23) — replace CRTP and const/non-const overloads:**
```cpp
// Bad — CRTP boilerplate for static polymorphism
template <typename Derived>
struct Base {
    void interface() { static_cast<Derived*>(this)->impl(); }
};

// Good — deducing this (C++23)
struct Base {
    void interface(this auto&& self) { self.impl(); }
};
struct Derived : Base {
    void impl() { /* ... */ }
};

// Also eliminates const/non-const overload duplication:
struct Container {
    auto&& at(this auto&& self, size_t i) { return self.data_[i]; }
    // One function handles both const and non-const access
};
```

**std::generator (C++23 coroutine):**
```cpp
// Bad — manual iterator class for lazy sequence
class FibIterator { /* 50 lines of boilerplate */ };

// Good — coroutine generator
std::generator<int> fibonacci() {
    int a = 0, b = 1;
    while (true) {
        co_yield a;
        std::tie(a, b) = std::pair{b, a + b};
    }
}

// Compose with ranges
for (auto n : fibonacci() | std::views::take(10) | std::views::filter(is_even)) {
    std::cout << n << '\n';
}
```

**Fold Expressions (C++17) — variadic template operations:**
```cpp
// Bad — recursive template instantiation
template <typename T> T sum(T v) { return v; }
template <typename T, typename... Args> T sum(T first, Args... rest) { return first + sum(rest...); }

// Good — fold expression
template <typename... Args>
auto sum(Args... args) { return (... + args); }

// Print all args with separator
template <typename... Args>
void print(Args&&... args) {
    ((std::cout << args << ' '), ...);
    std::cout << '\n';
}
```

---

## Anti-Patterns

**God class** — split by single responsibility:
```cpp
// Bad
class Application { void parse(); void render(); void query_db(); void send_email(); };
// Good
class ConfigParser { /* ... */ };
class Renderer { /* ... */ };
```

**`using namespace std` in headers** — pollutes every includer:
```cpp
// Bad (in .h)       // Good (in .cpp)
using namespace std;  using std::string; using std::vector;
```

**Macro overuse:**
```cpp
// Bad
#define SQUARE(x) ((x) * (x))
// Good
constexpr auto square(auto x) { return x * x; }
```

**shared_ptr as default:**
```cpp
// Bad — "just in case"              // Good — upgrade only when proven
auto w = std::make_shared<Widget>(); auto w = std::make_unique<Widget>();
```

---

## Reference Repo Patterns (Pre-extracted)

> When designing C++ classes/modules, apply these patterns from real-world production repos.
> Do NOT just list rules — structure your code like these repos do.

### fmtlib/fmt (23k stars) — API Extension Patterns

**Pattern 1: formatter<T> specialization for custom type formatting**

When you need to make a user type formattable, specialize `formatter<T>` with `parse()` + `format()`:

```cpp
// User extends the library by specializing formatter in their namespace
template <>
struct fmt::formatter<Point> {
    // Parse format spec (e.g., "{:}" or "{:.2f}")
    constexpr auto parse(format_parse_context& ctx) -> format_parse_context::iterator {
        return ctx.begin();  // no custom spec
    }
    // Format the value
    auto format(const Point& p, format_context& ctx) const -> format_context::iterator {
        return fmt::format_to(ctx.out(), "({}, {})", p.x, p.y);
    }
};
// Usage: fmt::format("pos={}", point);
```

**Design intent**: Two-method interface (parse + format) separates spec parsing from rendering.
Inherit from existing formatters to reuse standard specifiers.

**Pattern 2: format_as() ADL for simple type aliases**

```cpp
// Simpler alternative: just define format_as() in the type's namespace
enum class Color { Red, Green, Blue };
auto format_as(Color c) -> std::string_view {
    switch (c) {
        case Color::Red:   return "red";
        case Color::Green: return "green";
        case Color::Blue:  return "blue";
    }
}
// Usage: fmt::format("color={}", Color::Red);  // "color=red"
```

**Design intent**: ADL finds `format_as()` automatically — zero coupling to fmt library.
Use for enums and thin wrappers. Use `formatter<T>` for complex types.

**Pattern 3: Compile-time format string validation**

```cpp
// fmt validates format strings at compile time via constexpr parsing
auto msg = fmt::format("{} has {} items", name, count);  // checked at compile time
// Mismatch between args and placeholders → compile error, not runtime crash
```

**Apply this**: Use `std::format` (C++20) or fmtlib for ALL string formatting.
Never use `sprintf`/`snprintf`/`stringstream`.

---

### abseil/abseil-cpp (17k stars) — Module & Error Patterns

**Pattern 1: StatusOr<T> — Result type for error handling without exceptions**

```cpp
// Function returns value OR error — caller MUST check
absl::StatusOr<Config> LoadConfig(std::string_view path) {
    auto content = ReadFile(path);
    if (!content.ok()) return content.status();  // propagate error

    auto parsed = ParseYaml(*content);
    if (!parsed.ok()) return absl::InvalidArgumentError("bad yaml");

    return Config{*parsed};
}

// Caller
auto config = LoadConfig("app.yaml");
if (!config.ok()) {
    LOG(ERROR) << config.status();
    return;
}
UseConfig(*config);  // operator* accesses the value
```

**Design intent**: Errors are values, not exceptions. Caller can't ignore errors
(`ABSL_MUST_USE_RESULT`). Use `std::expected<T,E>` (C++23) as standard equivalent.

**Pattern 2: LogSink — Abstract interface for extensible logging**

```cpp
// Abstract sink with Send(LogEntry) + Flush()
class LogSink {
public:
    virtual ~LogSink() = default;
    virtual void Send(const LogEntry& entry) = 0;  // pure virtual, thread-safe
    virtual void Flush() {}                          // optional, for buffered sinks
};

// LogEntry carries structured metadata — not just a string
struct LogEntry {
    LogSeverity severity;
    absl::Time timestamp;
    std::string_view message;
    std::string_view source_filename;
    int source_line;
};
```

**Apply this**: When designing any interface that accepts pluggable backends (sinks, handlers,
strategies), pass a **structured data object** (not a formatted string). This lets backends
filter, route, or transform based on metadata.

**Pattern 3: Module directory structure — self-contained per feature**

```
absl/
  status/         # StatusOr, Status — own BUILD + CMakeLists
  log/            # Log, LogSink, LogEntry — own BUILD + CMakeLists
  strings/        # StrCat, StrFormat — own BUILD + CMakeLists
  container/      # flat_hash_map, btree — own BUILD + CMakeLists
```

**Apply this**: Each module has its own headers + sources + build config.
Public API in top-level headers, implementation in `internal/` subdirectory.

---

### TheLartians/ModernCppStarter (5k stars) — Project Template

**Pattern: CMake with generator expressions for build/install separation**

```cmake
cmake_minimum_required(VERSION 3.14...3.22)
project(MyLib VERSION 1.0 LANGUAGES CXX)

# Dependencies via CPM (declarative, version-pinned)
include(cmake/CPM.cmake)
CPMAddPackage("gh:fmtlib/fmt#10.2.1")

# Library target — scoped includes, not global
add_library(mylib src/core.cpp src/parser.cpp)
target_include_directories(mylib
    PUBLIC  $<BUILD_INTERFACE:${PROJECT_SOURCE_DIR}/include>
            $<INSTALL_INTERFACE:include/${PROJECT_NAME}-${PROJECT_VERSION}>
    PRIVATE src)
target_link_libraries(mylib PRIVATE fmt::fmt)
target_compile_features(mylib PUBLIC cxx_std_20)

# Tests in separate directory
if(PROJECT_IS_TOP_LEVEL)
    add_subdirectory(test)
endif()
```

**Apply this**: Always use `target_*` commands (never `include_directories()`/`link_libraries()`).
`$<BUILD_INTERFACE>` / `$<INSTALL_INTERFACE>` for proper header relocation.

**Directory layout**:
```
project/
  CMakeLists.txt
  cmake/CPM.cmake         # dependency manager
  include/mylib/           # public headers (users include these)
    core.hpp
    parser.hpp
  src/                     # private implementation
    core.cpp
    parser.cpp
    internal/              # internal headers not exposed
  test/
    CMakeLists.txt
    test_core.cpp
  standalone/              # executable entry point (if app, not lib)
    main.cpp
```

---

### nlohmann/json (49k stars) — Type Extension via ADL

**Pattern 1: to_json / from_json free functions**

```cpp
// Define in YOUR namespace — ADL finds them automatically
struct Person {
    std::string name;
    int age;
};

// Serialization: your type → json
void to_json(nlohmann::json& j, const Person& p) {
    j = nlohmann::json{{"name", p.name}, {"age", p.age}};
}

// Deserialization: json → your type
void from_json(const nlohmann::json& j, Person& p) {
    j.at("name").get_to(p.name);
    j.at("age").get_to(p.age);
}

// Usage — library calls your functions via ADL
nlohmann::json j = Person{"Alice", 30};     // implicit to_json
auto p = j.get<Person>();                    // implicit from_json
```

**Design intent**: Zero coupling — your type never includes json.hpp.
The library finds your functions through ADL (same namespace as your type).

**Pattern 2: Macro for boilerplate elimination**

```cpp
// For simple struct-to-json mapping, use the intrusive macro
struct Config {
    std::string host;
    int port;
    bool verbose;
    NLOHMANN_DEFINE_TYPE_INTRUSIVE(Config, host, port, verbose)
};
// Automatically generates to_json/from_json for listed members
```

**Pattern 3: Modular internal structure**

```
include/nlohmann/
  json.hpp                  # public API (single include)
  detail/
    conversions/            # to_json, from_json dispatchers
    iterators/              # iterator implementation
    input/                  # parser, lexer
    output/                 # serializer
    meta/                   # type traits, void_t, is_detected
```

**Apply this**: Public API = one header. Complex implementation = `detail/` or `internal/`
subdirectory. Never expose implementation headers to users.

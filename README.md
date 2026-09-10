# RegScope

RegScope is a behavioral diffing library for Python functions. It records what
a function did during a controlled test run so behavior can be compared across
code versions.

RegScope does not prove that two functions are mathematically equivalent. It
reports differences in behavior observed during the runs that were recorded.

## Current status

The early v0.1 core supports:

- Synchronous and asynchronous `@track` decoration
- Execution duration measurement
- Exception counting while preserving the original exception
- Flat call-graph counts using `sys.setprofile()`
- Structured JSON behavior profiles
- N-run JSON baselines with atomic file replacement
- Configurable baseline storage through `baseline_dir`
- Zero required runtime dependencies

## Quick start

```python
from regscope import track


@track(baseline_dir=".regscope")
def calculate_total(values: list[int]) -> int:
    return sum(values)


total = calculate_total([1, 2, 3])
profile = calculate_total.last_profile
print(total)
print(profile.duration_ns)
```

The decorator supports both `@track` and `@track(...)`. Async functions are
supported transparently:

```python
from regscope import track


@track(baseline_dir=".regscope")
async def fetch_value() -> int:
    return 42
```

Each tracked function writes a bounded JSON baseline to the configured
directory. The default directory is `.regscope`. Profiles contain structured
metrics and call counts; they do not capture function arguments or sensitive
external data.

## Limitations

- `sys.setprofile()` is process-global. RegScope restores an existing profiler,
  but concurrent profiler ownership is not yet supported.
- Profiles describe observed executions, not all possible behavior.
- Comparison reporting and CI baseline transport are still under development.
- Database, HTTP, Redis, and memory collectors are planned for later versions.

## Development

Install development dependencies and run the tests:

```bash
.venv/bin/python -m pip install ".[dev]"
.venv/bin/python -m pytest
```

The implementation roadmap is in [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md).

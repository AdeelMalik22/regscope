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

## Privacy and measurements

Profiles contain aggregate timing, call, exception, collector, and memory
metrics. RegScope does not capture function arguments, return values, SQL
text, bound parameters, URLs, headers, request bodies, Redis keys, or Redis
values. The SHA-256 fingerprint is derived from the structured profile and is
not a substitute for the profile itself.

The core call profiler adds measurable overhead, especially for functions with
large call graphs. Run the local benchmark with:

```bash
.venv/bin/python -m benchmarks.overhead
```

Benchmark results depend on the machine and Python version. Use them to tune
thresholds for a project rather than treating the sample output as universal.

## Schema stability

Structured profiles, baselines, and historical trend points currently use
schema version `1`. Older records that omit a schema field are read as version
1. Records from a newer unsupported schema are rejected explicitly so they
cannot be silently misinterpreted.

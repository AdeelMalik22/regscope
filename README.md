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

Use `warmup_runs=N` to execute and report the first N calls without adding
them to the baseline or historical trend. This is useful when the first call
opens connections, imports modules, or initializes caches:

```python
@track(baseline_dir=".regscope", warmup_runs=1)
def load_dashboard() -> int:
    return 42
```

The decorator supports both `@track` and `@track(...)`. Async functions are
supported transparently:

```python
from regscope import track


@track(baseline_dir=".regscope")
async def fetch_value() -> int:
    return 42
```

After a call, `function.get_current_profile()` and
`function.get_current_comparison()` return values stored in the current
`contextvars` context. These accessors are task-safe for concurrent async
invocations. The legacy `function.last_profile` and
`function.last_comparison` attributes remain available as compatibility
snapshots, but can be overwritten by another concurrent invocation.

Each tracked function writes a bounded JSON baseline to the configured
directory. The default directory is `.regscope`. Profiles contain structured
metrics and call counts; they do not capture function arguments or sensitive
external data.

## CI regression checks

The repository workflow keeps trusted baselines outside Git. A push to
`master` runs `tests/ci_targets`, records the baseline in `.regscope`, and
uploads it as the `regscope-baseline-master` artifact. Pull-request jobs
download the latest successful artifact from `master` and compare the same
targets against it. A comparison that exceeds the configured threshold fails
the job.

Baseline artifacts are retained for 30 days. The workflow includes hidden
files when uploading because `.regscope` is a dot-directory. The baseline
publisher is restricted to trusted `master` pushes; pull requests cannot
replace the trusted artifact, including pull requests from forks.

To reproduce the comparison locally, first generate a trusted baseline and
then run the targets without the update flag:

```bash
REGSCOPE_CI_BASELINE=1 REGSCOPE_TRUSTED_BASELINE=1 \
  .venv/bin/python -m pytest tests/ci_targets \
  --regscope-baseline-dir .regscope --regscope-update-baseline

REGSCOPE_CI_BASELINE=1 .venv/bin/python -m pytest tests/ci_targets \
  --regscope-baseline-dir .regscope
```

If no artifact has been published yet, the pull-request job reports that the
trusted baseline is unavailable and the comparison target fails rather than
silently treating the missing baseline as a pass.

## Limitations

- `sys.setprofile()` has one active profiler per current thread. RegScope
  restores the profiler observed at entry, and independent threads have
  independent collection contexts. RegScope does not arbitrate nested owners
  in one thread or an external profiler that replaces its hook during an
  execution. Run tracked profiling in an isolated test context when coverage,
  a debugger, or another profiler must remain active.
- HTTP and Redis collectors temporarily replace process-global library hooks.
  They restore the hook that was present when attached, are thread-safe for
  counting calls, and should not be attached concurrently by multiple
  tracked executions.
- Profiles describe observed executions, not all possible behavior.
- The CI artifact workflow is validated on trusted `master` runs; a real
  pull-request event is still required to exercise GitHub's fork permissions
  and artifact-download path end to end.

## Development

Install development dependencies and run the tests:

```bash
.venv/bin/python -m pip install ".[dev]"
.venv/bin/python -m pytest
```

The implementation roadmap is in [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md).
Release history is in [CHANGELOG.md](CHANGELOG.md), with the release policy in
[VERSIONING.md](VERSIONING.md).
Performance and threshold guidance is in [docs/performance.md](docs/performance.md).

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

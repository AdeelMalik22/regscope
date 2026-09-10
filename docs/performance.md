# Performance and threshold guidance

## Benchmark result

The development benchmark compares a recursive workload with and without
RegScope call-graph collection:

```text
baseline_median_seconds=0.000047494
instrumented_median_seconds=0.000822528
overhead_percent=1631.86
```

These values were measured on the development environment and are
machine-dependent. Call-graph instrumentation is intentionally observable on
small, call-heavy functions because `sys.setprofile()` receives an event for
each Python call.

Run the benchmark locally before making performance-sensitive threshold
decisions:

```bash
.venv/bin/python -m benchmarks.overhead
```

## Threshold policy

The default comparison threshold remains **20%**. It applies to the difference
between two equally instrumented observations, not to the overhead of an
uninstrumented function versus a tracked function. Raising the threshold to
hide instrumentation overhead would make genuine regressions harder to detect.

For especially small or call-heavy functions, teams should reduce collection
scope or configure a metric-specific threshold based on repeated benchmark
runs. Baselines and current profiles must always be collected with the same
RegScope configuration.

The benchmark is a noise-floor diagnostic, not a pass/fail performance test.
Its output should be considered alongside CI variance, Python version, and
workload size.

## Profiler ownership

Call-graph collection temporarily installs a `sys.setprofile()` callback for
the current thread and restores the callback that was active before
collection. Independent threads can collect independently. RegScope
deliberately does not arbitrate nested profiler owners in one thread or an
external profiler that replaces its hook during execution: coverage tools,
debuggers, pytest plugins, and application code may also depend on this hook.
Keep call-graph collection isolated when another tool must own the profiler
for the same execution.

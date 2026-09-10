# RegScope Implementation Plan

This plan turns `regscope_idea.md` into incremental, independently committed
implementation work. Each milestone is completed, tested, committed, and
pushed before the next milestone begins.

## Working rules

- Keep each commit focused on one plan step or one bug fix.
- Do not include unrelated files or IDE metadata in feature commits.
- Run the relevant tests before every commit.
- Push every commit immediately after it is created.
- Preserve the zero-required-runtime-dependency promise.
- Keep optional integrations lazy and isolated behind clear errors.

## Phase 0 — Project foundation

### Commit 1: package skeleton, packaging, and CI foundation

- Lock the project name to **RegScope**: package/import path `regscope` and CLI
  command `regscope`.
- Create the `regscope/` package and test package.
- Add package metadata and a `pyproject.toml` with stdlib-only runtime
  dependencies and development extras.
- Add a minimal public package version, type hints, and a `py.typed` marker.
- Add the initial test configuration and CI matrix for supported Python
  versions (3.9–3.12 initially).
- Validate sdist and wheel build/install in CI before feature work begins.

### Commit 2: documentation and repository hygiene

- Add a README with the observed-behavior disclaimer, MVP scope, and quick
  start direction.
- Add a focused `.gitignore`.
- Keep `regscope_idea.md` as the product specification.


## Phase 1 — v0.1 tracking core

### Commit 3: data model and deterministic serialization

- Define dataclasses for a per-run behavior profile and stored baseline.
- Include function identity, runtime, call count, exceptions, call graph data,
  metadata, schema version, and collection timestamps.
- Implement canonical JSON serialization so equivalent records hash alike.
- Add unit tests for round trips, schema versioning, and stable ordering.

### Commit 4: timing, exception, and call-count collection

- Implement synchronous tracking using `time.perf_counter()`.
- Capture successful and exceptional runs without hiding the original
  exception or changing the wrapped function's return value.
- Add call tracking with `sys.setprofile()` and restore any prior profiler in
  a `finally` block.
- Define the v0.1 limitation: profiling is process-global and concurrent
  tracking/profiler ownership is unsupported; document the limitation.
- Test nested calls, exceptions, recursion, profiler restoration, and running
  under an existing profiler/coverage session without corrupting its data.

### Commit 5: call-graph representation

- Finalize the v0.1 representation as a flat mapping of qualified function
  names to call counts, with the tracked function as the root.
- Exclude internal collector implementation frames.
- Document that this is an observed call summary, not a complete semantic
  execution graph.
- Add deterministic tests for graph output.

### Commit 6: async decorator support

- Make the decorator detect coroutine functions with
  `inspect.iscoroutinefunction`.
- Collect the same profile around awaited execution.
- Preserve metadata, return values, and exception behavior.
- Add async tests without requiring third-party test dependencies in runtime.

### Commit 7: `@track` public API and configuration

- Expose `track` from the package root.
- Support both `@track` and `@track(...)` in v0.1.
- Make `baseline_dir` an explicit optional decorator/configuration setting,
  with a documented default; do not add per-call parameter capture.
- Add public API tests.

## Phase 2 — baseline storage and comparison

### Commit 8: JSON baseline storage

- Store N runs per function, defaulting to five.
- Use atomic file replacement to avoid corrupting baselines on interruption.
- Include package/schema version and enough metadata to detect incompatible
  records.
- Add tests for creation, append, retention, malformed files, and safe failure.
- Use a lock or per-function files so parallel workers cannot overwrite one
  another; test concurrent writes and pytest-xdist-style isolation.

### Commit 9: noise-aware comparison engine

- Compare new observations against the previous run distribution rather than
  a single value.
- Start with an explicit configurable **20% default threshold**; keep the
  engine extensible for standard-deviation thresholds later.
- Report median, range, delta, percentage change, and regression status.
- Treat missing metrics and incompatible schemas as explicit outcomes.
- Add tests for stable values, noisy values, outliers, and threshold boundaries.

### Commit 10: derived fingerprint

- Generate a SHA-256 fingerprint from the canonical structured profile.
- Use it only as a fast change-detection shortcut.
- Ensure comparison explanations remain available from structured data.
- Add hash stability and meaningful-change tests.

## Phase 3 — v0.2 SQLAlchemy collector

### Commit 11: optional SQL query collector

- Add a SQLAlchemy extra and lazy import path.
- Count executed SQL statements through SQLAlchemy event hooks. Never capture
  raw SQL text, table names, bound parameters, or query results in profiles or
  baselines; this is a permanent count-only privacy constraint.
- Keep the base package importable without SQLAlchemy installed.
- Raise a clear installation message when the collector is requested without
  its extra.
- Test dependency-present and dependency-absent paths.

## Phase 4 — v0.3 CLI and v0.4 CI integration

### Commit 12: argparse comparison CLI

- Add `funcdna compare` using only `argparse` and the core comparison engine.
- Render the documented human-readable regression report.
- Add machine-readable output if it can be introduced without complicating
  the core interface.
- Test successful comparisons, detected regressions, malformed input, and
  exit status.

### Commit 13: persistent CI baseline workflow design

- Define the baseline transport before implementing the plugin: CI artifacts
  are the default persistence mechanism, downloaded before comparison and
  uploaded only by the trusted target-branch baseline job.
- Document artifact naming, retention, missing-baseline behavior, and how a
  PR job receives the target branch baseline.
- Keep committed baselines and external object storage as future adapters,
  not hidden assumptions in the core API.

### Commit 14: pytest plugin and CI exit codes

- Add an optional pytest integration without making pytest a runtime
  dependency.
- Provide a first-class fixture or marker for recording and comparing tracked
  functions.
- Return non-zero status only for configured regressions or invalid setup.
- Test baseline creation, comparison failure, and clean CI runs.
- Test a fresh checkout with a downloaded baseline, missing artifacts, and
  baseline updates from the target branch.

### Commit 15: instrumentation overhead benchmark

- Benchmark tracking against an untracked synthetic deep-recursion and
  high-call-count workload across the supported Python versions.
- Record timing overhead and variance as the tool's measurement noise floor.
- Use the results to validate the 20% default threshold and document when
  users should disable call-graph collection.

## Phase 5 — later collectors and v1.0 stabilization

Implement one integration at a time, with its own commit sequence and
absent-dependency tests:

1. HTTP request counting (`requests`/`httpx`), v0.5.
2. Redis call counting, v0.6.
3. Memory tracking with `tracemalloc`, v0.7.
4. Stable baseline format, documented threshold tuning, and historical trend
   views for v1.0.

## Definition of done for each milestone

- The feature has focused tests and documentation.
- Existing tests pass.
- Optional dependencies are not imported on unrelated code paths.
- Public behavior and baseline schema changes are intentional and documented.
- The change is committed separately with a descriptive message.
- The commit is pushed to the configured remote before starting the next step.

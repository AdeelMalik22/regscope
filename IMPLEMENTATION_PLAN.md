# FunctionDNA Implementation Plan

This plan turns `redscope_idea.md` into incremental, independently committed
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

### Commit 1: package skeleton and development configuration

- Create the `funcdna/` package and test package.
- Add package metadata and a `pyproject.toml` with stdlib-only runtime
  dependencies and development extras.
- Add a minimal public package version and a clean import path.
- Add the initial test configuration.

### Commit 2: documentation and repository hygiene

- Add a README with the observed-behavior disclaimer, MVP scope, and quick
  start direction.
- Add a focused `.gitignore`.
- Keep the existing project idea document as the product specification.

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
- Test nested calls, exceptions, recursion, and profiler restoration.

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
- Support zero-config defaults first, including a configurable output/baseline
  directory and collector options where they are needed.
- Support decorator usage both as `@track` and with explicit options if that
  configuration is finalized during implementation.
- Add public API tests.

## Phase 2 — baseline storage and comparison

### Commit 8: JSON baseline storage

- Store N runs per function, defaulting to five.
- Use atomic file replacement to avoid corrupting baselines on interruption.
- Include package/schema version and enough metadata to detect incompatible
  records.
- Add tests for creation, append, retention, malformed files, and safe failure.

### Commit 9: noise-aware comparison engine

- Compare new observations against the previous run distribution rather than
  a single value.
- Start with explicit configurable percentage thresholds and a documented
  default; keep the engine extensible for standard-deviation thresholds later.
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
- Count executed SQL statements through SQLAlchemy event hooks.
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

### Commit 13: pytest plugin and CI exit codes

- Add an optional pytest integration without making pytest a runtime
  dependency.
- Provide a first-class fixture or marker for recording and comparing tracked
  functions.
- Return non-zero status only for configured regressions or invalid setup.
- Test baseline creation, comparison failure, and clean CI runs.

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


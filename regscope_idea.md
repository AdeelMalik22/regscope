# RegScope — Product Specification

**Status:** Product specification finalized. RegScope implementation is active
and the current package is an early `0.1.0.dev1` alpha release.

This document contains everything decided so far. It's meant to be handed to an AI (or a human) to produce a concrete implementation plan and begin work.

---

## 1. One-line pitch

**A behavioral diffing tool for Python functions — it tells you whether a code change altered what a function *does*, not just whether its output is still correct.**

## 2. Problem statement

A developer changes a function and all tests pass, but the new implementation may secretly:

- Take much longer
- Execute more database queries
- Make more HTTP requests
- Consume more memory
- Call unexpected functions
- Raise more exceptions
- Perform additional side effects

Traditional profilers show *current* behavior. APM tools show *production* behavior. Neither ties a behavioral change to a specific code change and diffs it — that's the gap this fills.

## 3. Positioning against existing tools

| Category | Examples | What they show | What they lack |
|---|---|---|---|
| Profilers | cProfile, py-spy, scalene | Current behavior, in detail | No memory of the past, no diffing |
| APM tools | Datadog, New Relic | Production behavior over time | No per-function before/after diff tied to a code change |
| **RegScope** | — | **Per-function behavioral diff, tied to a code change, run in CI** | — |

**Explicit non-claim:** RegScope does NOT claim two functions are mathematically equivalent. It compares *observed* runtime behavior between versions. This distinction appears in the README's first section to avoid misrepresenting what the tool guarantees.

## 4. Primary use cases (in priority order for MVP focus)

1. **CI/CD regression protection** — compare current behavior against a baseline in CI, fail the build on regression. *(Highest priority — see roadmap below.)*
2. **Performance regression detection** — catch when a code change makes a function slower or adds queries.
3. **Refactoring validation** — compare old vs. new implementation's observed behavior.
4. **Hidden side-effect detection** — unexpected DB writes, HTTP calls, file operations.
5. **Legacy code investigation** — understand what a complicated function actually does at runtime.

## 5. Example usage (target v0.1–v0.3 API shape)

```python
from regscope import track

@track
def get_user_dashboard(user_id):
    user = get_user(user_id)
    orders = get_orders(user_id)
    notifications = get_notifications(user_id)
    return {"user": user, "orders": orders, "notifications": notifications}
```

Baseline record (conceptual, not final schema):

```
Function: get_user_dashboard
Runtime:       121 ms
DB queries:      3
Redis calls:     1
HTTP calls:      0
Exceptions:      0
Memory:        2.1 MB
Fingerprint:   7a91c82f...
```

After a code change:

```
Function: get_user_dashboard
Runtime:       684 ms   ↑ 465%
DB queries:     17      ↑ 466%
Memory:        8.4 MB   ↑ 300%
Fingerprint:   91bc20aa...
```

Regression report:

```
⚠ BEHAVIORAL REGRESSION

Database queries: 3 → 17
Execution time:    121ms → 684ms
Memory:            2.1MB → 8.4MB

Risk: HIGH
```

CLI comparison output:

```
RegScope Comparison

get_user
    4ms → 5ms          +25%

get_orders
   21ms → 91ms         +333% ⚠

create_order
   43ms → 44ms           +2%

DB queries
    7 → 19             +171% ⚠

Result: 2 behavioral regressions detected
```

## 6. Architecture

```
                RegScope
                     │
             ┌───────┴───────┐
             ↓               ↓
         Collectors      Fingerprint
             │               │
     ┌───────┼───────┐       ↓
     ↓       ↓       ↓    Comparison
   Python   DB      HTTP      │
   calls   calls    calls     ↓
                         Regression
                             │
                             ↓
                          CLI / CI
```

Collectors (planned, each optional beyond the Python one):
- **PythonCollector** (core, v0.1) — timing, call count, call graph, exceptions
- **PostgreSQL/SQLAlchemyCollector** (v0.2)
- **HTTPCollector** (v0.5)
- **RedisCollector** (v0.6)
- **MemoryCollector** (v0.7)

## 7. Four design decisions already locked in

These shape the v0.1 data model — decided in advance specifically to avoid a rewrite later.

### 7.1 Target environment: CI/test-suite runs, not prod sampling
v1.0 targets CI and local test runs — controlled inputs, no user-facing latency risk. Prod-sampling is an explicit non-goal for v1.0 (could be a v2.0+ idea, but must not creep into early scope since it has completely different overhead requirements).

### 7.2 Noise handling: N-run baselines, not single-run
Store **N runs per baseline** (default suggestion: 5), not a single value. Report a range/median. Flag a regression only when the new value falls **outside the previous distribution**, not just "bigger than the last single run." This is the most important structural decision — without it, CI runs will flap on ordinary noise (cache warmth, GC timing, shared DB load) and teams will disable the tool.

### 7.3 Structured data is primary; the fingerprint is a derived checksum
Store the full structured metric record every run. The fingerprint (hash) is only a fast "did anything change" shortcut to skip full comparison — never the primary artifact. This avoids ever hitting a fingerprint mismatch with no underlying data to explain why.

### 7.4 One collector at a time, done well
Do not build Postgres + Redis + HTTP collectors simultaneously. Each is its own integration-maintenance burden (API surface changes, version drift, connection pooling edge cases). Ship one collector fully before starting the next (see roadmap).

## 8. Tech stack

**Core principle: pure Python, zero required runtime dependencies** — same pattern validated in the author's other library, RequestGuard (confirmed via `pip show` that RequestGuard ships with zero required deps and puts everything else behind extras).

### Core (v0.1) — stdlib only
| Need | stdlib tool |
|---|---|
| Timing | `time.perf_counter()` |
| Call tracking / call graph | `sys.setprofile()` (per-call events; lighter than `sys.settrace`, which fires per-line) |
| Exception capture | try/except inside the decorator wrapper |
| Memory | `tracemalloc` (no `psutil` needed for basic peak/current delta) |
| Fingerprint/checksum | `hashlib` (sha256 over the structured record) |
| Baseline storage | `json` + `dataclasses` |
| Decorator plumbing | `functools.wraps`, `inspect` (use `inspect.iscoroutinefunction` to support both sync and async functions transparently) |

### Collectors (v0.2+) — optional extras, lazy-imported
```
pip install regscope[db]      # SQLAlchemy event hooks
pip install regscope[http]    # requests/httpx patching
pip install regscope[redis]   # redis-py instrumentation
pip install regscope[integration]  # supported integrations
```
Each collector's import must be lazy and guarded, only touched when that specific collector is invoked. On a missing optional dependency, raise a clear message ("install `regscope[db]` to use SQL query tracking") rather than crashing on import of the whole package or crashing on an unrelated code path.

**Cautionary precedent:** In testing RequestGuard, a real bug was found where a Flask-specific code branch did an unconditional `from flask import g` triggered by duck-typing on a `remote_addr` attribute — this crashed with `ModuleNotFoundError` for *any* object with that attribute, even unrelated to Flask, since Flask isn't a required dependency. **Every optional-integration import path in RegScope must be wrapped in try/except ImportError with a graceful fallback or clear error, and explicitly tested with that dependency absent.**

### CLI
Use **`argparse`** (stdlib) for v0.1–v0.3 to preserve the zero-required-dependency promise end-to-end, including the CLI. A `regscope[cli]` extra with `typer`/`click` for a nicer UX can be added later without breaking the dependency-free base install.

### Dev/test tooling (not shipped to end users)
`pytest`, `pytest-asyncio`, `build`, `twine` — as a `[dev]` extra, same shape as RequestGuard.

## 9. Roadmap

| Version | Scope |
|---|---|
| v0.1 | `@track` decorator; timing, call count, exceptions, call graph; N-run baselines; structured JSON storage; fingerprint as a derived checksum; sync + async support |
| v0.2 | SQL query counting via SQLAlchemy event hooks (one ORM, done well) |
| v0.3 | `regscope compare` CLI with the regression report format shown above (argparse-based) |
| v0.4 | pytest plugin / CI-friendly exit codes — first-class pytest fixture, not just a CLI wrapper. *(Moved up from later in the original draft — this is the strongest use case and validates the real CI pipeline story early, before sinking time into collectors nobody's asked to test yet.)* |
| v0.5 | HTTP call counting (via `requests`/`httpx` patching) |
| v0.6 | Redis call counting |
| v0.7 | Memory tracking via `tracemalloc` (save for last — trickiest to make low-noise) |
| v1.0 | Stable baseline format, documented noise-threshold tuning, historical trend view |

## 10. Naming — finalized

Candidates considered, with PyPI availability as last checked (verify again before committing — search coverage isn't exhaustive):

| Name | Notes |
|---|---|
| **`regscope`** | Selected package and project name. It communicates regression-scoped behavior checks and matches the published import and CLI names. |
| **`behaviordiff`** | Most literal match to the "behavioral diffing" positioning. No exact conflict found. Less distinctive/brandable than a coined name. |
| `regscope` | Portmanteau of "regression" + "scope" (as in microscope/telescope — an instrument you point at code to see regressions). Reads professional, in the vein of `line_profiler`/`memory_profiler`. Downside: doesn't hint at the cross-version diffing angle on its own — a README/tagline has to do that work. |
| ~~`functrace`~~ | **Taken** (unrelated function-call tracer). |
| ~~`pytrace`~~ | **Taken** (unrelated function tracer). |
| ~~`pydrifter`~~ | **Taken**, and in an awkwardly adjacent space (ML data-drift detection) — real risk of user confusion. |
| ~~`drift`/`pydrift`~~ | Too generic, high collision risk in the ML-monitoring "drift" naming space. |

**Final naming decision:** `regscope`. The package name, import path, CLI command, repository, and documentation use RegScope consistently.

## 11. Naming nuance for internal terminology

"Fingerprint" implies identity/equivalence, which the project explicitly disclaims. Consider calling the per-run record a **"behavior profile"** or **"trace,"** and reserve "fingerprint" purely for the derived checksum, to keep internal naming consistent with the external positioning.

## 12. Open questions for the next planning pass

These were flagged during design discussion but not yet resolved — worth addressing in the implementation plan:

- Exact JSON schema for a stored baseline (single run vs. N-run distribution — decided N-run, but field-level schema not yet drafted)
- Threshold/tolerance configuration format for what counts as "outside the previous distribution" (fixed %, stddev-based, configurable per-metric?)
- Whether `sys.setprofile()` conflicts with other profiling/debugging tools already active in a user's process (e.g., coverage.py, debuggers) — needs a compatibility check
- Call graph depth/representation — full call tree vs. flat call-count-by-function
- Whether v0.1 should support parameterizing `@track` (e.g., `@track(baseline_dir=...)`) or use zero-config sane defaults first

# RegScope Contribution Guide

## Project purpose

RegScope is a pure-Python behavioral diffing library. It compares observed
runtime behavior of functions across code versions. It does not claim to prove
mathematical equivalence between implementations.

The core runtime must remain dependency-free. Optional integrations belong in
isolated modules and must be lazy-imported with clear errors when their extra
dependency is unavailable.

## Repository layout

- `regscope/`: installable library package
- `regscope/api/`: public APIs and decorators
- `regscope/core/`: execution and comparison primitives
- `regscope/collectors/`: behavior collectors such as call-graph tracking
- `regscope/storage/`: baseline persistence adapters
- `tests/`: focused unit and integration tests
- `regscope_idea.md`: product specification
- `IMPLEMENTATION_PLAN.md`: ordered implementation roadmap

Add new files to the directory responsible for their concern. Avoid placing
feature modules directly in the package root unless they are package-level
public entry points.

## Development rules

- Preserve synchronous and asynchronous behavior of decorated functions.
- Do not capture sensitive data such as SQL text, bound parameters, request
  bodies, or function arguments in behavior profiles.
- Keep structured records as the source of truth; derived fingerprints are
  only shortcuts.
- Treat `sys.setprofile()` as process-global and preserve/restore an existing
  profiler around collection.
- Use the configured project interpreter for tests and tools.
- Add tests with every behavior change, including exceptional paths.

## Verification

Run the test suite from the repository root:

```bash
.venv/bin/python -m pytest
```

The project’s declared runtime dependencies must remain empty. Development
tools may be listed under the `dev` optional extra.

## Commit and push workflow

Every meaningful change is handled independently:

1. Make one focused change.
2. Add or update its tests.
3. Run the relevant verification.
4. Commit with a concise, descriptive message.
5. Push immediately to the configured remote.

Do not bundle unrelated fixes, infrastructure changes, or refactors into a
feature commit. Keep the working tree changes that belong to the user intact.

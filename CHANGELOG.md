# Changelog

All notable changes to RegScope are documented here.

## Unreleased

- Documented and remotely verified the trusted GitHub Actions baseline
  artifact flow.
- Clarified baseline privacy, retention, missing-artifact behavior, and local
  reproduction steps.
- Completed release verification for the Python 3.9–3.12 CI matrix, sdist and
  wheel installation, CLI entry points, schema migration checks, and overhead
  benchmarking.
- Confirmed the current development release is `0.1.0.dev1`; no 1.0.0
  compatibility promise is being claimed yet.
- Continued v0.1 release-readiness work.

## 0.1.0.dev1

- Alpha development release for early users and CI validation.
- Includes tracking, comparison, optional collectors, historical trends,
  pytest integration, and trusted CI baseline artifacts.

## 0.1.0.dev0

- Added synchronous and asynchronous `@track` instrumentation.
- Added timing, exception, call-graph, memory, and optional integration
  collectors.
- Added structured JSON profiles, bounded baselines, fingerprints, comparison
  reports, historical trends, CLI commands, and pytest integration.
- Added trusted CI baseline artifact workflows.

# Versioning and release policy

RegScope uses semantic versioning once the public API reaches 1.0. Until then,
development releases use the `0.1.0.devN` style and may change APIs while the
core design is finalized. `0.1.0.dev1` is an alpha development release and
does not promise a frozen public API.

## Compatibility guarantees

- The package version identifies the Python API and CLI release.
- Baseline/profile/history `schema_version` identifies persisted data format
  compatibility independently from the package version.
- Older records without a schema field are interpreted as schema version 1.
- Unsupported future schemas are rejected explicitly rather than silently
  misread.
- A schema change requires a migration path or a documented breaking-change
  note before release.

## Current v1 schema/API baseline

The persisted profile, baseline, and history formats are currently at
`schema_version: 1`. Version 1 guarantees deterministic JSON serialization,
explicit rejection of unsupported future schemas, and compatibility for
records that omit the schema field as version 1. The public v0.x API is still
developmental; these schema guarantees do not imply that the Python API is
frozen until the 1.0 release.

## Release checklist

Before a release:

1. Update the version in `pyproject.toml` and `regscope/__init__.py`.
2. Move the relevant Unreleased entries into `CHANGELOG.md`.
3. Run the full supported Python matrix and optional integration tests.
4. Build and install both sdist and wheel artifacts.
5. Verify CLI help, baseline compatibility, and schema migration behavior.
6. Tag the release using `v<version>`.

## CI baseline compatibility

CI baseline artifacts are disposable transport for schema-versioned records;
they are not a second versioning system. A release or schema change must
preserve the migration rules above. When the schema changes, publish a fresh
trusted `master` artifact before expecting pull requests to compare against
the new format.

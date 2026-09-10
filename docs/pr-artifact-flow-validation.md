# Pull-request artifact flow validation

This document exists to exercise the `pull_request` path in GitHub Actions.
The workflow should download the latest successful `regscope-baseline-master`
artifact and compare `tests/ci_targets` against it without updating the
trusted baseline.

This validation branch is intentionally harmless and can be deleted after the
workflow run completes.

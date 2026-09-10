"""Generate and compare the repository's trusted CI behavior baseline."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional, Sequence

from regscope import track


def baseline_target() -> int:
    """Small deterministic workload used only to validate the CI pipeline."""
    total = 0
    for value in range(500):
        total += value * value
    return total


def run(directory: Path) -> int:
    tracked = track(baseline_dir=directory, max_runs=5)(baseline_target)
    result = tracked()
    if result != 41_541_750:
        raise RuntimeError("CI baseline target returned an unexpected result")
    comparison = tracked.last_comparison
    if comparison is not None and comparison.regression:
        print("RegScope regression detected in trusted CI target")
        return 1
    print(f"RegScope baseline target recorded in {directory}")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("generate", "check"))
    parser.add_argument("--directory", type=Path, default=Path(".regscope"))
    args = parser.parse_args(argv)
    return run(args.directory)


if __name__ == "__main__":
    raise SystemExit(main())

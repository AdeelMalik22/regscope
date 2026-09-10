"""Generate and compare the repository's trusted CI behavior baseline."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional, Sequence

from regscope import track


def baseline_target() -> int:
    """Small deterministic workload used only to validate the CI pipeline."""
    total = 0
    for value in range(100_000):
        total += value * value
    return total


def run(directory: Path, repeats: int = 1, enforce: bool = True) -> int:
    tracked = track(baseline_dir=directory, max_runs=5)(baseline_target)
    for _ in range(repeats):
        result = tracked()
        if result != 333_328_333_350_000:
            raise RuntimeError("CI baseline target returned an unexpected result")
        comparison = tracked.last_comparison
        if enforce and comparison is not None and comparison.regression:
            print("RegScope regression detected in trusted CI target")
            return 1
    print(f"RegScope baseline target recorded in {directory}")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("generate", "check"))
    parser.add_argument("--directory", type=Path, default=Path(".regscope"))
    args = parser.parse_args(argv)
    return run(
        args.directory,
        repeats=5 if args.command == "generate" else 1,
        enforce=args.command == "check",
    )


if __name__ == "__main__":
    raise SystemExit(main())

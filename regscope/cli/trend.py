"""Historical trend reporting for RegScope."""

from pathlib import Path

from ..trends import HistoryStore


def report(directory: Path, function: str) -> int:
    summary = HistoryStore(directory).summarize(function)
    print("RegScope Trend")
    print(function)
    print(f"  Samples: {summary.samples}")
    print(f"  Duration: {summary.duration_min_ns} -> {summary.duration_median_ns} -> {summary.duration_max_ns} ns")
    print(f"  Exception samples: {summary.exception_samples}")
    return 0

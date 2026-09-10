"""Historical trend reporting for RegScope."""

from pathlib import Path
import json
from dataclasses import asdict

from ..trends import HistoryStore


def report(directory: Path, function: str, json_output: bool = False) -> int:
    summary = HistoryStore(directory).summarize(function)
    if json_output:
        print(json.dumps(asdict(summary), sort_keys=True))
        return 0
    print("RegScope Trend")
    print(function)
    print(f"  Samples: {summary.samples}")
    print(f"  Duration: {summary.duration_min_ns} -> {summary.duration_median_ns} -> {summary.duration_max_ns} ns")
    print(f"  Exception samples: {summary.exception_samples}")
    print(f"  Duration change: {summary.duration_delta_ns:+d} ns ({summary.duration_change_ratio:+.1%})")
    print(f"  Exception rate: {summary.exception_rate:.1%}")
    return 0

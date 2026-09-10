"""Measure the overhead of RegScope call-graph instrumentation.

Run with:

    .venv/bin/python -m benchmarks.overhead
"""

from __future__ import annotations

import argparse
import statistics
import timeit
from typing import Callable, List, Tuple

from regscope.collectors.call_graph import collect_call_graph


RECOMMENDED_THRESHOLD = 0.20


def recursive_workload(depth: int) -> int:
    if depth <= 0:
        return 1
    return recursive_workload(depth - 1) + 1


def run_benchmark(repeat: int = 7, number: int = 100) -> Tuple[float, float, float]:
    """Return baseline seconds, instrumented seconds, and overhead percent."""
    baseline = _timings(lambda: recursive_workload(40), repeat, number)
    instrumented = _timings(
        lambda: collect_call_graph(recursive_workload, 40), repeat, number
    )
    baseline_median = statistics.median(baseline)
    instrumented_median = statistics.median(instrumented)
    overhead = ((instrumented_median / baseline_median) - 1) * 100
    return baseline_median, instrumented_median, overhead


def _timings(work: Callable[[], object], repeat: int, number: int) -> List[float]:
    return timeit.repeat(work, repeat=repeat, number=number)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeat", type=int, default=7)
    parser.add_argument("--number", type=int, default=100)
    args = parser.parse_args()
    baseline, instrumented, overhead = run_benchmark(args.repeat, args.number)
    print(f"baseline_median_seconds={baseline:.9f}")
    print(f"instrumented_median_seconds={instrumented:.9f}")
    print(f"overhead_percent={overhead:.2f}")
    print(f"recommended_regression_threshold={RECOMMENDED_THRESHOLD:.0%}")


if __name__ == "__main__":
    main()

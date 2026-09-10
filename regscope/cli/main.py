"""Argparse-based RegScope command line interface."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Optional, Sequence

from ..core.comparison import DEFAULT_THRESHOLD, compare
from ..models import Baseline, BehaviorProfile
from .trend import report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="regscope")
    subparsers = parser.add_subparsers(dest="command", required=True)
    compare_parser = subparsers.add_parser("compare", help="compare a profile to a baseline")
    compare_parser.add_argument("--baseline", required=True, type=Path)
    compare_parser.add_argument("--current", required=True, type=Path)
    compare_parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    trend_parser = subparsers.add_parser("trend", help="report historical behavior trends")
    trend_parser.add_argument("--directory", type=Path, default=Path(".regscope"))
    trend_parser.add_argument("--function", required=True)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "compare":
        return _compare(args.baseline, args.current, args.threshold)
    if args.command == "trend":
        return report(args.directory, args.function)
    return 2


def _compare(baseline_path: Path, current_path: Path, threshold: float) -> int:
    baseline = Baseline.from_json(baseline_path.read_text(encoding="utf-8"))
    current = BehaviorProfile.from_json(current_path.read_text(encoding="utf-8"))
    result = compare(current, baseline, threshold=threshold)

    print("RegScope Comparison")
    print()
    print(result.function)
    for metric in result.metrics:
        marker = " REGRESSION" if metric.regression else ""
        print(
            f"  {metric.metric}: {metric.baseline_median:g} -> "
            f"{metric.current:g} ({metric.change_ratio:+.1%}){marker}"
        )
    print()
    if result.regression:
        print("Result: behavioral regression detected")
        return 1
    print("Result: no behavioral regression detected")
    return 0

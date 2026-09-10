"""Noise-aware comparison of observed behavior profiles."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Dict, Iterable, List, Mapping, Optional

from ..models import Baseline, BehaviorProfile


DEFAULT_THRESHOLD = 0.20


@dataclass(frozen=True)
class MetricComparison:
    metric: str
    current: float
    baseline_median: float
    delta: float
    change_ratio: float
    regression: bool
    threshold: float


@dataclass(frozen=True)
class ComparisonResult:
    function: str
    metrics: List[MetricComparison]
    status: str = "compared"

    @property
    def regression(self) -> bool:
        return any(metric.regression for metric in self.metrics)

    @property
    def risk(self) -> str:
        regressions = sum(metric.regression for metric in self.metrics)
        if regressions == 0:
            return "none"
        if any(metric.metric == "exceptions" and metric.regression for metric in self.metrics):
            return "high"
        return "medium" if regressions > 1 else "low"


def compare(
    current: BehaviorProfile,
    baseline: Baseline,
    threshold: float = DEFAULT_THRESHOLD,
    thresholds: Optional[Mapping[str, float]] = None,
) -> ComparisonResult:
    """Compare ``current`` with the baseline's observed metric distribution."""
    if not 0 <= threshold < 1:
        raise ValueError("threshold must be between 0 and 1")
    if current.function != baseline.function:
        raise ValueError("profile function does not match baseline function")
    if not baseline.runs:
        return ComparisonResult(function=current.function, metrics=[], status="baseline_missing")

    metrics = []
    for name in ("duration_ns", "call_count", "exceptions"):
        current_value = float(getattr(current, name))
        baseline_values = [float(getattr(run, name)) for run in baseline.runs]
        baseline_median = float(median(baseline_values))
        delta = current_value - baseline_median
        change_ratio = _change_ratio(current_value, baseline_median)
        metric_threshold = (thresholds or {}).get(name, threshold)
        if not 0 <= metric_threshold < 1:
            raise ValueError("metric thresholds must be between 0 and 1")
        metrics.append(
            MetricComparison(
                metric=name,
                current=current_value,
                baseline_median=baseline_median,
                delta=delta,
                change_ratio=change_ratio,
                regression=_is_regression(
                    current_value, baseline_median, metric_threshold, name
                ),
                threshold=metric_threshold,
            )
        )
    return ComparisonResult(function=current.function, metrics=metrics)


def _change_ratio(current: float, baseline: float) -> float:
    if baseline == 0:
        return 0.0 if current == 0 else float("inf")
    return (current - baseline) / baseline


def _is_regression(
    current: float, baseline: float, threshold: float, metric: str
) -> bool:
    if metric == "exceptions" and baseline == 0:
        return current > 0
    if baseline == 0:
        return current > 0
    return current > baseline * (1 + threshold)

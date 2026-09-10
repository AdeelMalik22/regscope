import pytest

from regscope.core.comparison import DEFAULT_THRESHOLD, compare
from regscope.models import Baseline, BehaviorProfile


def make_profile(duration_ns: int, calls: int = 2, exceptions: int = 0) -> BehaviorProfile:
    return BehaviorProfile(
        function="example.work",
        duration_ns=duration_ns,
        call_count=calls,
        exceptions=exceptions,
    )


def baseline() -> Baseline:
    result = Baseline(function="example.work")
    result.add(make_profile(100))
    result.add(make_profile(110))
    result.add(make_profile(90))
    return result


def test_compare_reports_medians_and_deltas() -> None:
    result = compare(make_profile(120), baseline())
    duration = next(metric for metric in result.metrics if metric.metric == "duration_ns")

    assert duration.baseline_median == 100
    assert duration.delta == 20
    assert duration.change_ratio == pytest.approx(0.2)
    assert result.regression is False


def test_compare_flags_values_above_default_threshold() -> None:
    result = compare(make_profile(121), baseline())

    assert result.regression is True
    assert any(metric.regression for metric in result.metrics)


def test_compare_flags_new_exceptions_when_baseline_is_clean() -> None:
    result = compare(make_profile(100, exceptions=1), baseline())

    exception_metric = next(metric for metric in result.metrics if metric.metric == "exceptions")
    assert exception_metric.regression is True


def test_compare_handles_empty_baseline() -> None:
    result = compare(make_profile(100), Baseline(function="example.work"))

    assert result.metrics == []
    assert result.regression is False
    assert result.status == "baseline_missing"


def test_compare_validates_inputs() -> None:
    with pytest.raises(ValueError, match="threshold"):
        compare(make_profile(100), baseline(), threshold=1)
    with pytest.raises(ValueError, match="does not match"):
        compare(make_profile(100), Baseline(function="other.work"))


def test_compare_supports_metric_thresholds_and_risk() -> None:
    result = compare(
        make_profile(115, exceptions=1), baseline(), thresholds={"duration_ns": 0.5}
    )

    assert not next(metric for metric in result.metrics if metric.metric == "duration_ns").regression
    assert result.risk == "high"

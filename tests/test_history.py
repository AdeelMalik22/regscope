from pathlib import Path

import pytest

from regscope.models import BehaviorProfile
from regscope.trends import HistoryStore, TrendPoint


def profile(duration: int, exceptions: int = 0) -> BehaviorProfile:
    return BehaviorProfile(
        function="example.work", duration_ns=duration, exceptions=exceptions
    )


def test_history_records_and_round_trips_timestamped_points(tmp_path: Path) -> None:
    store = HistoryStore(tmp_path)
    point = store.record(profile(100), recorded_at="2026-01-01T00:00:00+00:00")

    loaded = store.load("example.work")

    assert loaded == [point]
    assert isinstance(point, TrendPoint)
    assert point.fingerprint == profile(100).fingerprint()


def test_history_summarizes_duration_trend(tmp_path: Path) -> None:
    store = HistoryStore(tmp_path)
    store.record(profile(100))
    store.record(profile(200, exceptions=1))
    store.record(profile(300))

    summary = store.summarize("example.work")

    assert summary.samples == 3
    assert summary.duration_min_ns == 100
    assert summary.duration_median_ns == 200
    assert summary.duration_max_ns == 300
    assert summary.exception_samples == 1


def test_history_requires_samples_for_summary(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no historical samples"):
        HistoryStore(tmp_path).summarize("missing.function")


def test_history_retains_latest_points(tmp_path: Path) -> None:
    store = HistoryStore(tmp_path, max_points=2)
    store.record(profile(100))
    store.record(profile(200))
    store.record(profile(300))

    assert [point.duration_ns for point in store.load("example.work")] == [200, 300]


def test_history_migrates_records_without_schema_version(tmp_path: Path) -> None:
    store = HistoryStore(tmp_path)
    path = store.path_for("example.work")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '{"function":"example.work","recorded_at":"2026-01-01T00:00:00+00:00",'
        '"duration_ns":100,"call_count":0,"exceptions":0,"fingerprint":"old"}\n',
        encoding="utf-8",
    )

    assert store.load("example.work")[0].schema_version == 1

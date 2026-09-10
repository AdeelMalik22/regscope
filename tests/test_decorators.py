import pytest

from regscope import TrackConfig, track


def test_track_preserves_function_behavior_and_profile(tmp_path) -> None:
    @track(baseline_dir=tmp_path)
    def add(left: int, right: int) -> int:
        return left + right

    assert add(2, 3) == 5
    assert add.__name__ == "add"
    assert add.last_profile is not None
    assert add.last_profile.function.endswith("test_track_preserves_function_behavior_and_profile.<locals>.add")
    assert add.last_profile.exceptions == 0
    assert add.last_profile.call_graph
    assert add.last_comparison.metrics == []

    add(3, 4)
    assert add.last_comparison.function == add.last_profile.function
    assert add.last_comparison.metrics


def test_track_records_exception_and_reraises_it(tmp_path) -> None:
    @track(baseline_dir=tmp_path)
    def fail() -> None:
        raise ValueError("expected")

    with pytest.raises(ValueError, match="expected"):
        fail()

    assert fail.last_profile.exceptions == 1
    assert len(list(tmp_path.glob("*.json"))) == 1


def test_track_does_not_mask_original_exception_when_persistence_fails(
    tmp_path, monkeypatch
) -> None:
    from regscope.storage import BaselineStore

    def fail_to_append(self, profile):
        raise OSError("storage unavailable")

    monkeypatch.setattr(BaselineStore, "append", fail_to_append)

    @track(baseline_dir=tmp_path)
    def fail() -> None:
        raise ValueError("application failure")

    with pytest.raises(ValueError, match="application failure"):
        fail()


def test_track_surfaces_persistence_failure_after_success(tmp_path, monkeypatch) -> None:
    from regscope.storage import BaselineStore

    def fail_to_append(self, profile):
        raise OSError("storage unavailable")

    monkeypatch.setattr(BaselineStore, "append", fail_to_append)

    @track(baseline_dir=tmp_path)
    def succeed() -> str:
        return "ok"

    with pytest.raises(OSError, match="storage unavailable"):
        succeed()


def test_track_preserves_application_exception_when_collector_cleanup_fails(
    tmp_path, monkeypatch
) -> None:
    from regscope.api import decorators

    class FailingCollectorContext:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            raise OSError("collector cleanup failed")

    monkeypatch.setattr(
        decorators, "active_collectors", lambda config, metrics: FailingCollectorContext()
    )

    @track(baseline_dir=tmp_path)
    def fail() -> None:
        raise ValueError("application failure")

    with pytest.raises(ValueError, match="application failure") as raised:
        fail()

    assert isinstance(raised.value.__cause__, OSError)


def test_track_config_controls_baseline_retention(tmp_path) -> None:
    @track(baseline_dir=tmp_path, max_runs=1)
    def add(value: int) -> int:
        return value

    add(1)
    add(2)
    baseline_file = next(tmp_path.glob("*.json"))

    assert '"duration_ns"' in baseline_file.read_text(encoding="utf-8")
    assert TrackConfig(max_runs=1).max_runs == 1


def test_track_config_rejects_invalid_retention(tmp_path) -> None:
    with pytest.raises(ValueError, match="at least 1"):
        track(baseline_dir=tmp_path, max_runs=0)


def test_track_discards_configured_warmup_runs(tmp_path) -> None:
    @track(baseline_dir=tmp_path, warmup_runs=1)
    def add(value: int) -> int:
        return value

    assert add(1) == 1
    assert add.last_comparison.status == "warmup"
    assert list(tmp_path.glob("*.json")) == []

    assert add(2) == 2
    assert add.last_comparison.status == "baseline_missing"
    assert len(list(tmp_path.glob("*.json"))) == 1


def test_track_config_rejects_negative_warmup_runs(tmp_path) -> None:
    with pytest.raises(ValueError, match="must not be negative"):
        track(baseline_dir=tmp_path, warmup_runs=-1)


def test_track_can_collect_memory_metrics(tmp_path) -> None:
    @track(baseline_dir=tmp_path, collect_memory=True)
    def allocate() -> int:
        return len([object() for _ in range(100)])

    assert allocate() == 100
    assert allocate.last_profile.metrics["memory_peak"] > 0
    assert "memory_current_delta" in allocate.last_profile.metrics


def test_track_records_historical_trend_point(tmp_path) -> None:
    @track(baseline_dir=tmp_path, history_dir=tmp_path / "history")
    def work() -> int:
        return 1

    work()

    assert len(list((tmp_path / "history").glob("*.jsonl"))) == 1

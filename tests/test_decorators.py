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

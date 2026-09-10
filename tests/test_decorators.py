import pytest

from regscope import track


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


def test_track_records_exception_and_reraises_it(tmp_path) -> None:
    @track(baseline_dir=tmp_path)
    def fail() -> None:
        raise ValueError("expected")

    with pytest.raises(ValueError, match="expected"):
        fail()

    assert fail.last_profile.exceptions == 1
    assert len(list(tmp_path.glob("*.json"))) == 1

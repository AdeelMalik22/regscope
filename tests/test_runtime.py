import pytest

from regscope.core.runtime import measure_sync


def test_measure_sync_preserves_result_and_records_duration() -> None:
    def add(left: int, right: int) -> int:
        return left + right

    result, observed = measure_sync(add, 2, 3)

    assert result == 5
    assert observed.function.endswith("test_measure_sync_preserves_result_and_records_duration.<locals>.add")
    assert observed.duration_ns >= 0
    assert observed.exceptions == 0


def test_measure_sync_reraises_original_exception() -> None:
    error = RuntimeError("expected")
    profiles = []

    def fail() -> None:
        raise error

    with pytest.raises(RuntimeError) as raised:
        measure_sync(fail, profile_sink=profiles.append)

    assert raised.value is error
    assert len(profiles) == 1
    assert profiles[0].exceptions == 1

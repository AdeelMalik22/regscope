import json

import pytest

from regscope.models import Baseline, BehaviorProfile


def profile(duration_ns: int = 100) -> BehaviorProfile:
    return BehaviorProfile(
        function="example.work",
        duration_ns=duration_ns,
        call_count=3,
        exceptions=0,
        call_graph={"example.work": 1, "example.child": 2},
        metadata={"z": "last", "a": "first"},
    )


def test_profile_json_round_trip() -> None:
    original = profile()
    assert BehaviorProfile.from_json(original.to_json()) == original


def test_profile_json_is_canonical() -> None:
    value = profile().to_json()
    assert value == BehaviorProfile.from_dict(json.loads(value)).to_json()
    assert value.index('"a":"first"') < value.index('"z":"last"')


def test_profile_fingerprint_is_stable_and_derived() -> None:
    original = profile()
    restored = BehaviorProfile.from_json(original.to_json())

    assert original.fingerprint() == restored.fingerprint()
    assert len(original.fingerprint()) == 64


def test_profile_fingerprint_changes_when_structured_data_changes() -> None:
    assert profile(100).fingerprint() != profile(101).fingerprint()


def test_baseline_keeps_latest_five_runs() -> None:
    baseline = Baseline(function="example.work")
    for duration in range(6):
        baseline.add(profile(duration))

    assert [item.duration_ns for item in baseline.runs] == [1, 2, 3, 4, 5]


def test_baseline_rejects_a_different_function() -> None:
    baseline = Baseline(function="example.work")
    different = BehaviorProfile(function="other.work", duration_ns=1)

    with pytest.raises(ValueError, match="does not match"):
        baseline.add(different)


def test_baseline_json_round_trip() -> None:
    baseline = Baseline(function="example.work")
    baseline.add(profile())

    assert Baseline.from_json(baseline.to_json()) == baseline


def test_baseline_rejects_zero_capacity() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        Baseline(function="example.work", max_runs=0).add(profile())

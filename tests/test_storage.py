from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import Process

import pytest

from regscope.models import BehaviorProfile
from regscope.storage import BaselineStore


def make_profile(function: str = "example.work", duration_ns: int = 1) -> BehaviorProfile:
    return BehaviorProfile(function=function, duration_ns=duration_ns)


def append_values_in_process(directory: str, values) -> None:
    child_store = BaselineStore(directory, max_runs=12)
    for value in values:
        child_store.append(make_profile(duration_ns=value))


def test_store_loads_missing_function_as_empty_baseline(tmp_path: Path) -> None:
    store = BaselineStore(tmp_path)

    baseline = store.load("example.work")

    assert baseline.function == "example.work"
    assert baseline.runs == []
    assert not tmp_path.exists() or list(tmp_path.iterdir()) == []


def test_store_appends_and_retains_latest_runs(tmp_path: Path) -> None:
    store = BaselineStore(tmp_path, max_runs=2)
    for duration in (10, 20, 30):
        store.append(make_profile(duration_ns=duration))

    loaded = store.load("example.work")

    assert [run.duration_ns for run in loaded.runs] == [20, 30]
    assert len(list(tmp_path.glob("*.json"))) == 1


def test_store_uses_atomic_json_file(tmp_path: Path) -> None:
    store = BaselineStore(tmp_path)
    store.append(make_profile())
    path = store.path_for("example.work")

    assert path.parent == tmp_path
    assert path.suffix == ".json"
    assert path.read_text(encoding="utf-8").startswith("{")
    assert not list(tmp_path.glob("tmp*"))


def test_store_rejects_invalid_capacity(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="at least 1"):
        BaselineStore(tmp_path, max_runs=0)


def test_store_serializes_concurrent_appends(tmp_path: Path) -> None:
    store = BaselineStore(tmp_path, max_runs=20)

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(
            executor.map(
                lambda duration: store.append(make_profile(duration_ns=duration)),
                range(20),
            )
        )

    loaded = store.load("example.work")
    assert len(loaded.runs) == 20
    assert sorted(run.duration_ns for run in loaded.runs) == list(range(20))


def test_store_serializes_cross_process_appends(tmp_path: Path) -> None:
    store = BaselineStore(tmp_path, max_runs=12)

    first = Process(target=append_values_in_process, args=(str(tmp_path), range(0, 6)))
    second = Process(target=append_values_in_process, args=(str(tmp_path), range(6, 12)))
    first.start()
    second.start()
    first.join()
    second.join()

    assert first.exitcode == 0
    assert second.exitcode == 0
    loaded = store.load("example.work")
    assert sorted(run.duration_ns for run in loaded.runs) == list(range(12))

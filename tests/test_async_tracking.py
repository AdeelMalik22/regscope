import asyncio

import pytest

from regscope import track


def test_track_supports_async_functions(tmp_path) -> None:
    @track(baseline_dir=tmp_path)
    async def get_value() -> int:
        await asyncio.sleep(0)
        return 42

    assert asyncio.run(get_value()) == 42
    assert get_value.last_profile is not None
    assert get_value.last_profile.exceptions == 0
    assert get_value.last_profile.duration_ns >= 0
    assert get_value.last_comparison.metrics == []


def test_track_records_async_exception(tmp_path) -> None:
    @track(baseline_dir=tmp_path)
    async def fail() -> None:
        raise ValueError("expected")

    with pytest.raises(ValueError, match="expected"):
        asyncio.run(fail())

    assert fail.last_profile.exceptions == 1
    assert len(list(tmp_path.glob("*.json"))) == 1


def test_track_isolates_current_profile_between_async_tasks(tmp_path) -> None:
    @track(baseline_dir=tmp_path)
    async def get_value(value: int) -> int:
        await asyncio.sleep(0)
        return value

    async def invoke(value: int):
        result = await get_value(value)
        return result, get_value.get_current_profile()

    async def run_tasks():
        return await asyncio.gather(invoke(1), invoke(2))

    first, second = asyncio.run(run_tasks())

    assert first[0] == 1
    assert second[0] == 2
    assert first[1] is not None
    assert second[1] is not None
    assert first[1] is not second[1]

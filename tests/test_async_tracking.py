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


def test_track_records_async_exception(tmp_path) -> None:
    @track(baseline_dir=tmp_path)
    async def fail() -> None:
        raise ValueError("expected")

    with pytest.raises(ValueError, match="expected"):
        asyncio.run(fail())

    assert fail.last_profile.exceptions == 1
    assert len(list(tmp_path.glob("*.json"))) == 1

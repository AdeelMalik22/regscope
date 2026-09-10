import importlib.util

import pytest

from regscope.collectors import RedisCollector


def test_redis_collector_import_does_not_require_redis() -> None:
    assert RedisCollector is not None


def test_redis_collector_explains_missing_extra() -> None:
    if importlib.util.find_spec("redis") is not None:
        pytest.skip("redis is installed in this environment")

    with pytest.raises(RuntimeError, match=r"regscope\[redis\]"):
        RedisCollector().attach()

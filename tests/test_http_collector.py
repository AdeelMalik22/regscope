import importlib.util

import pytest

from regscope.collectors import HTTPCollector


def test_http_collector_import_does_not_require_requests() -> None:
    assert HTTPCollector is not None


def test_http_collector_explains_missing_extra() -> None:
    if importlib.util.find_spec("requests") is not None:
        pytest.skip("requests is installed in this environment")

    with pytest.raises(RuntimeError, match=r"regscope\[http\]"):
        HTTPCollector().attach()

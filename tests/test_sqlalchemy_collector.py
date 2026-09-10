import importlib.util

import pytest

from regscope.collectors import SQLAlchemyCollector


def test_sqlalchemy_collector_import_does_not_require_dependency() -> None:
    assert SQLAlchemyCollector is not None


def test_sqlalchemy_collector_explains_missing_extra() -> None:
    if importlib.util.find_spec("sqlalchemy") is not None:
        pytest.skip("SQLAlchemy is installed in this environment")

    with pytest.raises(RuntimeError, match=r"regscope\[db\]"):
        SQLAlchemyCollector().attach(object())

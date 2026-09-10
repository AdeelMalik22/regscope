from regscope.pytest_plugin import pytest_addoption


def test_pytest_plugin_is_importable_without_changing_core_api() -> None:
    assert callable(pytest_addoption)

"""Representative behavior target used by the CI baseline workflow."""

import os

import pytest
from regscope import track


pytestmark = pytest.mark.skipif(
    os.environ.get("REGSCOPE_CI_BASELINE") != "1",
    reason="CI baseline target",
)


@track(baseline_dir=".regscope-runtime")
def dashboard_total() -> int:
    return sum(value * value for value in range(100_000))


def test_dashboard_behavior(regscope_record) -> None:
    dashboard_total()
    profile = dashboard_total.last_profile
    assert profile is not None
    regscope_record(profile)

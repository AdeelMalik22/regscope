"""Optional pytest integration for baseline comparisons."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import pytest

from .core.comparison import DEFAULT_THRESHOLD, ComparisonResult, compare
from .models import BehaviorProfile
from .storage import BaselineStore


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("regscope")
    group.addoption(
        "--regscope-baseline-dir",
        action="store",
        default=".regscope",
        help="directory containing RegScope JSON baselines",
    )
    group.addoption(
        "--regscope-threshold",
        action="store",
        type=float,
        default=DEFAULT_THRESHOLD,
        help="allowed relative increase before a regression is reported",
    )


@pytest.fixture
def regscope_compare(request: pytest.FixtureRequest) -> Callable[[BehaviorProfile], ComparisonResult]:
    """Return a helper that compares a profile and fails on regression."""
    directory = Path(request.config.getoption("--regscope-baseline-dir"))
    threshold = request.config.getoption("--regscope-threshold")

    def compare_profile(profile: BehaviorProfile) -> ComparisonResult:
        baseline = BaselineStore(directory).load(profile.function)
        result = compare(profile, baseline, threshold=threshold)
        if result.regression:
            pytest.fail(f"RegScope behavioral regression detected for {profile.function}")
        return result

    return compare_profile

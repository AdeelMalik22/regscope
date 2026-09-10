"""Optional pytest integration for baseline comparisons."""

from __future__ import annotations

from pathlib import Path
from typing import Callable
import os

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
    group.addoption(
        "--regscope-update-baseline",
        action="store_true",
        help="update baselines only when REGSCOPE_TRUSTED_BASELINE=1",
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


@pytest.fixture
def regscope_record(request: pytest.FixtureRequest) -> Callable[[BehaviorProfile], ComparisonResult]:
    """Compare a profile and optionally record it in a trusted update run."""
    directory = Path(request.config.getoption("--regscope-baseline-dir"))
    threshold = request.config.getoption("--regscope-threshold")
    update_requested = request.config.getoption("--regscope-update-baseline")
    trusted = os.environ.get("REGSCOPE_TRUSTED_BASELINE") == "1"
    store = BaselineStore(directory)

    def record_profile(profile: BehaviorProfile) -> ComparisonResult:
        baseline = store.load(profile.function)
        result = compare(profile, baseline, threshold=threshold)
        if result.status == "baseline_missing" and not (update_requested and trusted):
            pytest.fail(f"RegScope baseline missing for {profile.function}")
        if result.regression and not (update_requested and trusted):
            pytest.fail(f"RegScope behavioral regression detected for {profile.function}")
        if update_requested and trusted:
            store.append(profile)
        return result

    return record_profile

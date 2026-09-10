"""Representative behavior target used by the CI baseline workflow."""

from regscope import track


@track(baseline_dir=".regscope-runtime")
def dashboard_total() -> int:
    return sum(value * value for value in range(100_000))


def test_dashboard_behavior(regscope_record) -> None:
    dashboard_total()
    profile = dashboard_total.last_profile
    assert profile is not None
    regscope_record(profile)

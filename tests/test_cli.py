import json

from regscope.cli import main
from regscope.models import Baseline, BehaviorProfile


def write_profiles(tmp_path, current_duration: int):
    baseline = Baseline(function="example.work")
    baseline.add(BehaviorProfile(function="example.work", duration_ns=100))
    baseline_path = tmp_path / "baseline.json"
    current_path = tmp_path / "current.json"
    baseline_path.write_text(baseline.to_json(), encoding="utf-8")
    current_path.write_text(
        BehaviorProfile(function="example.work", duration_ns=current_duration).to_json(),
        encoding="utf-8",
    )
    return baseline_path, current_path


def test_cli_reports_clean_comparison(tmp_path, capsys) -> None:
    baseline, current = write_profiles(tmp_path, 110)

    assert main(["compare", "--baseline", str(baseline), "--current", str(current)]) == 0
    assert "no behavioral regression" in capsys.readouterr().out


def test_cli_returns_failure_for_regression(tmp_path, capsys) -> None:
    baseline, current = write_profiles(tmp_path, 121)

    assert main(["compare", "--baseline", str(baseline), "--current", str(current)]) == 1
    assert "regression detected" in capsys.readouterr().out

import json

import pytest

from regscope.cli import main
from regscope.models import Baseline, BehaviorProfile


def write_profiles(
    tmp_path, current_duration: int, *, current_calls: int = 0, current_exceptions: int = 0
):
    baseline = Baseline(function="example.work")
    baseline.add(
        BehaviorProfile(
            function="example.work", duration_ns=100, call_count=2, exceptions=0
        )
    )
    baseline_path = tmp_path / "baseline.json"
    current_path = tmp_path / "current.json"
    baseline_path.write_text(baseline.to_json(), encoding="utf-8")
    current_path.write_text(
        BehaviorProfile(
            function="example.work",
            duration_ns=current_duration,
            call_count=current_calls,
            exceptions=current_exceptions,
        ).to_json(),
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


def test_cli_reports_trend(tmp_path, capsys) -> None:
    from regscope.models import BehaviorProfile
    from regscope.trends import HistoryStore

    store = HistoryStore(tmp_path)
    store.record(BehaviorProfile(function="example.work", duration_ns=100))

    assert main(["trend", "--directory", str(tmp_path), "--function", "example.work"]) == 0
    assert "RegScope Trend" in capsys.readouterr().out


def test_cli_reports_trend_as_json(tmp_path, capsys) -> None:
    from regscope.models import BehaviorProfile
    from regscope.trends import HistoryStore

    HistoryStore(tmp_path).record(
        BehaviorProfile(function="example.work", duration_ns=100)
    )

    assert main([
        "trend", "--directory", str(tmp_path), "--function", "example.work", "--json"
    ]) == 0
    assert '"duration_latest_ns": 100' in capsys.readouterr().out


def test_cli_supports_machine_readable_output(tmp_path, capsys) -> None:
    baseline, current = write_profiles(tmp_path, 121)

    assert main([
        "compare", "--baseline", str(baseline), "--current", str(current), "--json"
    ]) == 1
    assert '"risk": "low"' in capsys.readouterr().out


def test_cli_human_output_includes_all_metrics(tmp_path, capsys) -> None:
    baseline, current = write_profiles(tmp_path, 100, current_calls=3, current_exceptions=1)

    assert main(["compare", "--baseline", str(baseline), "--current", str(current)]) == 1
    output = capsys.readouterr().out

    assert "RegScope Comparison" in output
    assert "example.work" in output
    assert "duration_ns:" in output
    assert "call_count:" in output
    assert "exceptions:" in output
    assert "Risk: high" in output


def test_cli_json_output_is_valid_and_complete(tmp_path, capsys) -> None:
    baseline, current = write_profiles(tmp_path, 100)

    assert main([
        "compare", "--baseline", str(baseline), "--current", str(current), "--json"
    ]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["function"] == "example.work"
    assert payload["status"] == "compared"
    assert payload["regression"] is False
    assert payload["risk"] == "none"
    assert {metric["metric"] for metric in payload["metrics"]} == {
        "duration_ns", "call_count", "exceptions"
    }


def test_cli_supports_global_threshold(tmp_path, capsys) -> None:
    baseline, current = write_profiles(tmp_path, 119)

    assert main([
        "compare", "--baseline", str(baseline), "--current", str(current),
        "--threshold", "0.10",
    ]) == 1
    assert "regression detected" in capsys.readouterr().out


def test_cli_supports_metric_specific_threshold(tmp_path, capsys) -> None:
    baseline, current = write_profiles(tmp_path, 119)

    assert main([
        "compare", "--baseline", str(baseline), "--current", str(current),
        "--duration-threshold", "0.10",
    ]) == 1
    assert "duration_ns" in capsys.readouterr().out


def test_cli_reports_missing_baseline_without_regression(tmp_path, capsys) -> None:
    _, current = write_profiles(tmp_path, 100)
    missing = tmp_path / "missing.json"

    baseline = tmp_path / "empty-baseline.json"
    baseline.write_text(
        Baseline(function="example.work").to_json(), encoding="utf-8"
    )
    assert main([
        "compare", "--baseline", str(baseline), "--current", str(current)
    ]) == 0
    output = capsys.readouterr().out
    assert "Status: baseline_missing" in output
    assert not missing.exists()


def test_cli_rejects_invalid_threshold(tmp_path) -> None:
    baseline, current = write_profiles(tmp_path, 100)

    with pytest.raises(ValueError, match="threshold"):
        main([
            "compare", "--baseline", str(baseline), "--current", str(current),
            "--threshold", "1",
        ])


def test_cli_reports_malformed_profile(tmp_path) -> None:
    baseline, current = write_profiles(tmp_path, 100)
    current.write_text("not-json", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        main(["compare", "--baseline", str(baseline), "--current", str(current)])


def test_cli_requires_compare_paths() -> None:
    with pytest.raises(SystemExit):
        main(["compare"])


def test_cli_trend_json_is_parseable_with_multiple_samples(tmp_path, capsys) -> None:
    from regscope.trends import HistoryStore

    store = HistoryStore(tmp_path)
    store.record(BehaviorProfile(function="example.work", duration_ns=100))
    store.record(BehaviorProfile(function="example.work", duration_ns=200, exceptions=1))

    assert main([
        "trend", "--directory", str(tmp_path), "--function", "example.work", "--json"
    ]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["samples"] == 2
    assert payload["duration_latest_ns"] == 200
    assert payload["exception_samples"] == 1


def test_cli_trend_requires_function() -> None:
    with pytest.raises(SystemExit):
        main(["trend"])


def test_cli_trend_reports_empty_history_error(tmp_path) -> None:
    with pytest.raises(ValueError, match="no historical samples"):
        main(["trend", "--directory", str(tmp_path), "--function", "missing.function"])

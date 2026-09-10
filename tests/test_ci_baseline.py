from pathlib import Path

from scripts.ci_baseline import main


def test_ci_baseline_script_generates_and_checks(tmp_path: Path) -> None:
    assert main(["generate", "--directory", str(tmp_path)]) == 0
    assert main(["check", "--directory", str(tmp_path)]) == 0
    assert list(tmp_path.glob("*.json"))

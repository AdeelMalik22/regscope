import os
import subprocess
import sys

from regscope.models import Baseline, BehaviorProfile
from regscope.storage import BaselineStore
from regscope.pytest_plugin import pytest_addoption


def test_pytest_plugin_is_importable_without_changing_core_api() -> None:
    assert callable(pytest_addoption)


def test_plugin_works_in_real_pytest_subprocess(tmp_path) -> None:
    baseline_dir = tmp_path / "baseline"
    baseline_dir.mkdir()
    baseline = Baseline(function="sample.target")
    baseline.add(BehaviorProfile(function="sample.target", duration_ns=100))
    BaselineStore(baseline_dir).save(baseline)

    test_file = tmp_path / "test_sample.py"
    test_file.write_text(
        "from regscope.models import BehaviorProfile\n\n"
        "def test_profile(regscope_record):\n"
        "    regscope_record(BehaviorProfile(function='sample.target', duration_ns=110))\n",
        encoding="utf-8",
    )
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(tmp_path)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(test_file),
            "--regscope-baseline-dir",
            str(baseline_dir),
        ],
        env=environment,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_plugin_only_updates_with_trusted_flag(tmp_path) -> None:
    baseline_dir = tmp_path / "baseline"
    baseline_dir.mkdir()
    baseline = Baseline(function="sample.target")
    baseline.add(BehaviorProfile(function="sample.target", duration_ns=100))
    BaselineStore(baseline_dir).save(baseline)
    test_file = tmp_path / "test_sample.py"
    test_file.write_text(
        "from regscope.models import BehaviorProfile\n\n"
        "def test_profile(regscope_record):\n"
        "    regscope_record(BehaviorProfile(function='sample.target', duration_ns=200))\n",
        encoding="utf-8",
    )
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(tmp_path)
    command = [
        sys.executable, "-m", "pytest", str(test_file),
        "--regscope-baseline-dir", str(baseline_dir),
        "--regscope-update-baseline",
    ]
    untrusted = subprocess.run(command, env=environment, capture_output=True, text=True)
    assert untrusted.returncode != 0

    environment["REGSCOPE_TRUSTED_BASELINE"] = "1"
    trusted = subprocess.run(command, env=environment, capture_output=True, text=True)
    assert trusted.returncode == 0, trusted.stdout + trusted.stderr
    assert len(BaselineStore(baseline_dir).load("sample.target").runs) == 2

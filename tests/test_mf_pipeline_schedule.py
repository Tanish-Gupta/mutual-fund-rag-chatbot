from mf_pipeline.schedule import GITHUB_ACTIONS_CRON_UTC, schedule_summary


def test_github_cron_matches_ten_am_ist() -> None:
    """04:30 UTC == 10:00 India Standard Time."""
    assert GITHUB_ACTIONS_CRON_UTC == "30 4 * * *"


def test_schedule_summary_mentions_ist() -> None:
    s = schedule_summary()
    assert "10:00" in s
    assert "IST" in s
    assert "daily-pipeline.yml" in s


def test_cli_schedule_info_exits_zero() -> None:
    import os
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = ":".join(str(root / p) for p in ("phase1/src", "phase2/src", "phase3/src", "phase5/src"))
    r = subprocess.run(
        [sys.executable, "-m", "mf_pipeline", "--schedule-info"],
        cwd=str(root),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    assert "10:00" in r.stdout

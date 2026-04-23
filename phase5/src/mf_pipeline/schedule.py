"""Documented automation times for Phase 5 (keep in sync with deploy docs and GitHub Actions)."""

from __future__ import annotations

# GitHub Actions `on.schedule.cron` uses UTC. This string must match
# `.github/workflows/daily-pipeline.yml` (schedule → cron).
GITHUB_ACTIONS_CRON_UTC = "30 4 * * *"

# 04:30 UTC == 10:00 India Standard Time (IST); IST has no daylight saving.
SCHEDULE_GITHUB_SUMMARY = "Every day at 10:00 India Standard Time (IST) via GitHub Actions."
SCHEDULE_GITHUB_CRON_NOTE = (
    f"Cron is `{GITHUB_ACTIONS_CRON_UTC}` (UTC). Local macOS/Linux examples in docs/SCHEDULER.md use 10:00 machine local time."
)


def schedule_summary() -> str:
    return "\n".join(
        (
            SCHEDULE_GITHUB_SUMMARY,
            SCHEDULE_GITHUB_CRON_NOTE,
            "Workflow: .github/workflows/daily-pipeline.yml",
        )
    )


def print_schedule_info() -> None:
    print(schedule_summary())

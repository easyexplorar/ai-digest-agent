"""Decides whether a scheduled run should go ahead.

The Task Scheduler job has two triggers: the weekday 10:00 slot, and a
logon backup for days the PC was off or nobody was signed in at 10:00
(19 Oct 2026: booted 09:59, signed in 10:01, the 10:00 run was skipped).
Both launch `run_digest.py --scheduled`, so this guard keeps the backup
from sending early, on weekends, or a second time in one day.

Manual runs (no --scheduled) bypass the guard and never write the marker,
so a test run emailed only to the user doesn't block the real send.
"""

from datetime import datetime, time
from pathlib import Path

RUN_AT = time(10, 0)


def sent_marker(now: datetime, output_dir: str = "output") -> Path:
    return Path(output_dir) / f"sent_{now:%Y%m%d}.marker"


def skip_reason(now: datetime, output_dir: str = "output") -> str | None:
    """Why a scheduled run should not go ahead now, or None to proceed."""
    if now.weekday() >= 5:
        return "weekend"
    if now.time() < RUN_AT:
        return f"before {RUN_AT:%H:%M}"
    if sent_marker(now, output_dir).exists():
        return "today's digest already sent"
    return None


def mark_sent(now: datetime, output_dir: str = "output") -> Path:
    path = sent_marker(now, output_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(now.isoformat(timespec="seconds"), encoding="utf-8")
    return path

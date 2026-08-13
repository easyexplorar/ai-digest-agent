"""Persist daily ranked snapshots and compute trend deltas and discipline tallies."""

import json
from collections import Counter
from datetime import datetime, date, timedelta
from pathlib import Path


def save_snapshot(ranked_items: list[dict], output_dir: str = "output") -> Path:
    """Save today's top-30 ranked items as a JSON snapshot for future comparison."""
    out = Path(output_dir)
    out.mkdir(exist_ok=True)
    filename = out / f"snapshot_{date.today().strftime('%Y%m%d')}.json"
    snapshot = [
        {
            "title":      item["title"],
            "source":     item["source"],
            "url":        item["url"],
            "score":      item["score"],
            "discipline": item.get("discipline", "Other"),
            "reason":     item.get("reason", ""),
        }
        for item in ranked_items[:30]
    ]
    filename.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
    return filename


def load_snapshot(target_date: date, output_dir: str = "output") -> list[dict]:
    """Load a saved snapshot for a given date; returns [] if not found."""
    path = Path(output_dir) / f"snapshot_{target_date.strftime('%Y%m%d')}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return []


def load_yesterday(output_dir: str = "output") -> list[dict]:
    yesterday = date.today() - timedelta(days=1)
    # Step back up to 4 days to skip weekends
    for offset in range(1, 5):
        d = date.today() - timedelta(days=offset)
        snap = load_snapshot(d, output_dir)
        if snap:
            return snap
    return []


def load_seen_urls(output_dir: str = "output", days: int = 3) -> set[str]:
    """Return URLs present in top-30 snapshots from the past N days."""
    seen: set[str] = set()
    for offset in range(1, days + 1):
        d = date.today() - timedelta(days=offset)
        for item in load_snapshot(d, output_dir):
            if item.get("url"):
                seen.add(item["url"])
    return seen


def discipline_tally(ranked_items: list[dict], top_n: int = 15) -> dict[str, int]:
    """Count discipline labels across the top N ranked items."""
    counter = Counter(
        item.get("discipline", "Other")
        for item in ranked_items[:top_n]
    )
    return dict(counter.most_common())


def trend_delta(today_items: list[dict], yesterday_items: list[dict]) -> dict:
    """Split today's top items into 'new today' vs 'recurring from yesterday'."""
    yesterday_keys = {item["title"].lower()[:70] for item in yesterday_items}
    new_today  = [i for i in today_items[:15] if i["title"].lower()[:70] not in yesterday_keys]
    recurring  = [i for i in today_items[:15] if i["title"].lower()[:70] in yesterday_keys]
    return {"new": new_today, "recurring": recurring}


def format_tally_text(tally: dict[str, int]) -> str:
    if not tally:
        return "No discipline data available."
    return " | ".join(f"{disc}: {count}" for disc, count in tally.items())


def format_delta_text(delta: dict) -> str:
    new_titles       = [f"- {i['title']} ({i['source']})" for i in delta["new"][:5]]
    recurring_titles = [f"- {i['title']} ({i['source']})" for i in delta["recurring"][:3]]
    lines = [f"New today ({len(delta['new'])}):"]
    lines += new_titles or ["  (no prior data)"]
    lines += [f"\nRecurring from yesterday ({len(delta['recurring'])}):"]
    lines += recurring_titles or ["  (none)"]
    return "\n".join(lines)

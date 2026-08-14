"""Persist daily ranked snapshots and compute trend deltas and discipline tallies."""

import json
from collections import Counter
from datetime import datetime, date, timedelta
from pathlib import Path

from dedup_utils import normalize_title


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


def save_seen_urls(items: list[dict], output_dir: str = "output") -> Path:
    """Persist every item fetched today (not just the top-30 that make the
    snapshot) so tomorrow's run can skip all of them, not only the ones that
    happened to rank highly today."""
    out = Path(output_dir)
    out.mkdir(exist_ok=True)
    filename = out / f"urls_{date.today().strftime('%Y%m%d')}.json"
    urls = sorted({item["url"] for item in items if item.get("url")})
    filename.write_text(json.dumps(urls, indent=2), encoding="utf-8")
    return filename


def load_seen_urls(output_dir: str = "output", days: int = 3) -> set[str]:
    """Return URLs fetched in the past N days. Prefers the full urls_*.json
    log; falls back to the top-30 snapshot for older dates saved before that
    log existed, so historical runs still contribute some coverage."""
    seen: set[str] = set()
    for offset in range(1, days + 1):
        d = date.today() - timedelta(days=offset)
        urls_path = Path(output_dir) / f"urls_{d.strftime('%Y%m%d')}.json"
        if urls_path.exists():
            seen.update(json.loads(urls_path.read_text(encoding="utf-8")))
        else:
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
    yesterday_keys = {normalize_title(item["title"]) for item in yesterday_items}
    new_today  = [i for i in today_items[:15] if normalize_title(i["title"]) not in yesterday_keys]
    recurring  = [i for i in today_items[:15] if normalize_title(i["title"]) in yesterday_keys]
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


CHINA_DISCIPLINES = {"Chinese Lab Developments", "Chinese Embodied AI & Robotics"}


def format_china_context(ranked_items: list[dict], top_n: int = 5) -> str:
    """Build a dedicated text block of Chinese-lab/robotics items for the
    digest's China AI Watch section, pulled from the *full* ranked list
    rather than just the overall top N. Without this, that section only
    ever saw whatever made the overall top 10 by score — and agent/safety
    items routinely outscored Chinese model releases, so the section
    reported "nothing notable" even on days with several DeepSeek/Qwen/
    InternLM releases (verified against real ranked snapshots)."""
    china_items = [
        i for i in ranked_items if i.get("discipline") in CHINA_DISCIPLINES
    ][:top_n]
    if not china_items:
        return "No Chinese lab or robotics items detected today."
    return "\n".join(
        f"- [{i['source']}] {i['title']} — {i.get('reason', '')} ({i['url']})"
        for i in china_items
    )

"""Generates the Friday weekly rollup and strategic interpretation."""

from datetime import date, timedelta
from pathlib import Path
from openai import OpenAI

from grok_utils import generate_content_with_retry

MODEL = "grok-4-fast"


WEEKLY_PROMPT = """You are a senior AI research strategist writing a weekly intelligence report for a practitioner who monitors AI and agentic system trends.

You have the daily digests from this week below. Synthesise them into a weekly rollup with these exact sections:

---

## Week of {week_start} — Weekly Rollup

### Top Signals This Week
The 5 most important developments across the whole week. For each:
- Bold heading
- Which day(s) it appeared
- Why it mattered at the week level (not just the day)

### Discipline Breakdown
Which engineering disciplines dominated this week and which were quiet. Note any shifts mid-week.

### Emerging Threads
2–3 themes that appeared across multiple days and are building momentum. These are the ones to watch next week.

### Weekly Interpretation
A 150-word strategic read: what does this week's pattern mean for AI practitioners? What is accelerating, what is stalling, what should someone act on before it goes mainstream?

### Watch List for Next Week
3–5 specific topics, papers, repos, or organisations to monitor in the coming week based on this week's signals.

---

Keep the full rollup under 1000 words. Write for someone who has already read the daily digests — skip re-summarising, focus on the week-level synthesis.

Daily digests:
{daily_digests}
"""


def is_friday() -> bool:
    return date.today().weekday() == 4


def collect_week_digests(output_dir: str = "output") -> list[tuple[str, str]]:
    """Return (day_label, content) for each daily digest found this week (Mon–Fri)."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    found = []
    for i in range(5):
        day = monday + timedelta(days=i)
        if day > today:
            break
        pattern = f"digest_{day.strftime('%Y%m%d')}*.md"
        matches = sorted(Path(output_dir).glob(pattern))
        if matches:
            content = matches[-1].read_text(encoding="utf-8")
            found.append((f"{day_names[i]} {day.strftime('%d %b')}", content))
    return found


def generate_weekly_rollup(api_key: str, output_dir: str = "output") -> str:
    """Generate and save the weekly rollup. Returns the rollup text."""
    week_digests = collect_week_digests(output_dir)
    if not week_digests:
        return ""

    today = date.today()
    monday = today - timedelta(days=today.weekday())
    week_start = monday.strftime("%d %b %Y")

    combined = "\n\n---\n\n".join(
        f"**{label}:**\n{content}" for label, content in week_digests
    )

    client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
    prompt = WEEKLY_PROMPT.format(
        daily_digests=combined,
        week_start=week_start,
    )
    response = generate_content_with_retry(
        client,
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    rollup_text = response.choices[0].message.content.strip()

    out = Path(output_dir)
    filename = out / f"weekly_{today.strftime('%Y%m%d')}.md"
    filename.write_text(rollup_text, encoding="utf-8")
    return rollup_text

"""Main entry point — fetch, rank, summarise, notify, rollup."""

import os
import sys
import io

from datetime import date
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown

# On Windows, pass a UTF-8 wrapped stream directly to Console so Rich
# sees it at construction time rather than after the fact.
if sys.platform == "win32":
    _utf8_stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
else:
    _utf8_stdout = None

from sources.fetchers import fetch_all
from ranker import rank_items
from digest import generate_digest
from tracker import (
    save_snapshot, load_yesterday, load_seen_urls,
    discipline_tally, trend_delta,
    format_tally_text, format_delta_text,
)
from notify import save_digest, send_windows_notification
from weekly_rollup import is_friday, generate_weekly_rollup
from email_sender import send_digest_email, send_rollup_email

load_dotenv()
console = Console(file=_utf8_stdout) if _utf8_stdout else Console()


def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        console.print("[red]Error:[/red] GEMINI_API_KEY not set. Copy .env.example to .env and add your key.")
        sys.exit(1)

    # ── Fetch ──────────────────────────────────────────────────────────────
    console.print("[bold cyan]AI Digest Agent[/bold cyan] — fetching sources...")
    items = fetch_all()
    console.print(f"\n  Total: [bold]{len(items)}[/bold] items fetched across all sources.")

    if not items:
        console.print("[yellow]No items fetched. Check your internet connection.[/yellow]")
        sys.exit(0)

    # ── Filter already-seen items ──────────────────────────────────────────
    seen_urls = load_seen_urls()
    if seen_urls:
        before = len(items)
        items = [i for i in items if i.get("url") not in seen_urls]
        filtered = before - len(items)
        if filtered:
            console.print(f"  Skipped [bold]{filtered}[/bold] already-seen item(s) from recent snapshots.")

    # ── Rank ───────────────────────────────────────────────────────────────
    console.print("  Ranking with Gemini...")
    ranked = rank_items(items, api_key)

    # ── Trend & discipline analysis ────────────────────────────────────────
    yesterday = load_yesterday()
    tally     = discipline_tally(ranked)
    delta     = trend_delta(ranked, yesterday)
    tally_txt = format_tally_text(tally)
    delta_txt = format_delta_text(delta)

    console.print(f"  Discipline pulse: {tally_txt}")
    console.print(f"  New today: {len(delta['new'])} | Recurring: {len(delta['recurring'])}")

    # ── Generate digest ────────────────────────────────────────────────────
    console.print("  Generating digest...")
    digest_text = generate_digest(
        ranked, api_key,
        discipline_tally=tally_txt,
        trend_delta=delta_txt,
    )

    # ── Save ───────────────────────────────────────────────────────────────
    output_file   = save_digest(digest_text)
    snapshot_file = save_snapshot(ranked)
    console.print(f"  Digest  → [green]{output_file}[/green]")
    console.print(f"  Snapshot→ [green]{snapshot_file}[/green]\n")

    # ── Display ────────────────────────────────────────────────────────────
    console.print(Markdown(digest_text))

    # ── Notify ─────────────────────────────────────────────────────────────
    first_line = digest_text.split("\n")[0].lstrip("#").strip()
    send_windows_notification("AI Digest Ready", first_line)

    # ── Email daily digest ────────────────────────────────────────────────
    smtp_host = os.getenv("SMTP_HOST", "127.0.0.1")
    smtp_port = int(os.getenv("SMTP_PORT", "1025"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    email_to  = os.getenv("EMAIL_TO")

    if smtp_user and smtp_pass and email_to:
        date_label = date.today().strftime("%d %b %Y")
        try:
            send_digest_email(
                smtp_host, smtp_port, smtp_user, smtp_pass,
                email_to, digest_text, date_label,
            )
            console.print(f"  Email: [green]daily digest sent to {email_to}[/green]")
        except Exception as e:
            console.print(f"  Email: [red]daily digest failed — {e}[/red]")
    else:
        console.print("  Email: [yellow]skipped (SMTP_USER/SMTP_PASS/EMAIL_TO not set)[/yellow]")

    # ── Weekly rollup (Fridays only) ───────────────────────────────────────
    if is_friday():
        console.print("\n[bold yellow]Friday — generating weekly rollup...[/bold yellow]")
        rollup = generate_weekly_rollup(api_key)
        if rollup:
            console.print(Markdown(rollup))
            send_windows_notification(
                "Weekly AI Rollup Ready",
                "Your weekly AI trends interpretation is saved in the output folder.",
            )

            if smtp_user and smtp_pass and email_to:
                week_label = date.today().strftime("%d %b %Y")
                try:
                    send_rollup_email(
                        smtp_host, smtp_port, smtp_user, smtp_pass,
                        email_to, rollup, week_label,
                    )
                    console.print(f"  Email: [green]weekly rollup sent to {email_to}[/green]")
                except Exception as e:
                    console.print(f"  Email: [red]weekly rollup failed — {e}[/red]")


if __name__ == "__main__":
    main()

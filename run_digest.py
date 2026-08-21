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

from logging_setup import setup_logging
from sources.fetchers import fetch_all
from sources.market_data import fetch_market_data, format_market_context
from ranker import rank_items
from digest import generate_digest
from tracker import (
    save_snapshot, save_seen_urls, load_yesterday, load_seen_urls,
    discipline_tally, trend_delta,
    format_tally_text, format_delta_text, format_china_context, format_frontier_context,
)
from frontier_voices import tag_frontier_voices
from notify import save_digest, send_windows_notification
from weekly_rollup import is_friday, generate_weekly_rollup
from email_sender import send_digest_email, send_rollup_email
from retention import prune_output

load_dotenv()
# legacy_windows=False: skip Rich's Win32 console API path, which crashes
# (OSError: Invalid argument on flush) when there's no real console attached
# — e.g. a Task Scheduler run that fired while nothing was watching.
console = Console(file=_utf8_stdout, legacy_windows=False) if _utf8_stdout else Console(legacy_windows=False)
logger = setup_logging()


def main():
    logger.info("=== Run started ===")
    api_key = os.getenv("XAI_API_KEY")
    if not api_key:
        console.print("[red]Error:[/red] XAI_API_KEY not set. Copy .env.example to .env and add your key.")
        logger.error("XAI_API_KEY not set — aborting run.")
        send_windows_notification("AI Digest FAILED", "XAI_API_KEY not set — run aborted.")
        sys.exit(1)

    # ── Fetch ──────────────────────────────────────────────────────────────
    console.print("[bold cyan]AI Digest Agent[/bold cyan] — fetching sources...")
    items = fetch_all()
    tag_frontier_voices(items)
    console.print(f"\n  Total: [bold]{len(items)}[/bold] items fetched across all sources.")
    logger.info(f"Fetched {len(items)} items across all sources.")

    if not items:
        console.print("[yellow]No items fetched. Check your internet connection.[/yellow]")
        logger.warning("No items fetched — ending run early.")
        send_windows_notification("AI Digest FAILED", "No items fetched today — check your internet connection.")
        sys.exit(0)

    # Log every fetched URL today (not just whatever makes today's top-30
    # snapshot) so tomorrow's seen-URL filter has full coverage.
    save_seen_urls(items)

    # ── Filter already-seen items ──────────────────────────────────────────
    seen_urls = load_seen_urls()
    if seen_urls:
        before = len(items)
        items = [i for i in items if i.get("url") not in seen_urls]
        filtered = before - len(items)
        if filtered:
            console.print(f"  Skipped [bold]{filtered}[/bold] already-seen item(s) from recent snapshots.")

    # ── Rank ───────────────────────────────────────────────────────────────
    console.print("  Ranking with Grok...")
    ranked = rank_items(items, api_key)
    logger.info(f"Ranked {len(ranked)} items.")

    # ── Trend & discipline analysis ────────────────────────────────────────
    yesterday = load_yesterday()
    tally     = discipline_tally(ranked)
    delta     = trend_delta(ranked, yesterday)
    tally_txt = format_tally_text(tally)
    delta_txt = format_delta_text(delta)

    console.print(f"  Discipline pulse: {tally_txt}")
    console.print(f"  New today: {len(delta['new'])} | Recurring: {len(delta['recurring'])}")

    china_txt = format_china_context(ranked)
    frontier_txt = format_frontier_context(ranked)

    # ── Market signals ─────────────────────────────────────────────────────
    console.print("  Fetching market data...")
    try:
        market_txt = format_market_context(fetch_market_data())
    except Exception as e:
        console.print(f"  [yellow]Market data fetch failed — {e}[/yellow]")
        logger.warning(f"Market data fetch failed: {e}")
        market_txt = "Market data unavailable."

    # ── Generate digest ────────────────────────────────────────────────────
    console.print("  Generating digest...")
    digest_text = generate_digest(
        ranked, api_key,
        discipline_tally=tally_txt,
        trend_delta=delta_txt,
        market_context=market_txt,
        china_context=china_txt,
        frontier_context=frontier_txt,
    )
    logger.info("Digest generated.")

    # ── Save ───────────────────────────────────────────────────────────────
    output_file   = save_digest(digest_text)
    snapshot_file = save_snapshot(ranked)
    console.print(f"  Digest  → [green]{output_file}[/green]")
    console.print(f"  Snapshot→ [green]{snapshot_file}[/green]\n")
    logger.info(f"Saved digest to {output_file}, snapshot to {snapshot_file}.")

    # ── Prune old output ──────────────────────────────────────────────────
    try:
        pruned = prune_output(logger=logger)
        if pruned:
            console.print(f"  Pruned [dim]{len(pruned)} file(s) older than retention window.[/dim]")
    except Exception as e:
        console.print(f"  [yellow]Output pruning failed — {e}[/yellow]")
        logger.warning(f"Output pruning failed: {e}")

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
            logger.info(f"Daily digest emailed to {email_to}.")
        except Exception as e:
            console.print(f"  Email: [red]daily digest failed — {e}[/red]")
            logger.error(f"Daily digest email failed: {e}")
    else:
        console.print("  Email: [yellow]skipped (SMTP_USER/SMTP_PASS/EMAIL_TO not set)[/yellow]")
        logger.info("Email skipped — SMTP_USER/SMTP_PASS/EMAIL_TO not fully set.")

    # ── Weekly rollup (Fridays only) ───────────────────────────────────────
    if is_friday():
        console.print("\n[bold yellow]Friday — generating weekly rollup...[/bold yellow]")
        logger.info("Friday — generating weekly rollup.")
        try:
            rollup = generate_weekly_rollup(api_key)
        except Exception as e:
            # Isolated from the outer crash handler so a rollup failure
            # (e.g. Grok exhausting retries) can't take down a run whose
            # daily digest already succeeded and was already emailed above.
            console.print(f"  [red]Weekly rollup failed — {e}[/red]")
            logger.error(f"Weekly rollup generation failed: {e}")
            send_windows_notification("Weekly Rollup FAILED", f"Rollup generation failed: {e}")
        else:
            if rollup:
                console.print(Markdown(rollup))
                logger.info("Weekly rollup generated.")
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
                        logger.info(f"Weekly rollup emailed to {email_to}.")
                    except Exception as e:
                        console.print(f"  Email: [red]weekly rollup failed — {e}[/red]")
                        logger.error(f"Weekly rollup email failed: {e}")
            else:
                logger.warning("Weekly rollup produced no output (no daily digests found this week).")

    logger.info("=== Run finished ===")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        logger.exception("Run crashed with an unhandled exception.")
        send_windows_notification("AI Digest FAILED", f"Run crashed: {e}")
        raise

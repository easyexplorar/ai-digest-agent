# AI Digest Agent

Fetches AI/agentic-systems news from arXiv, lab blogs, and community sources, ranks it with Grok (xAI) for novelty and relevance, and emails a daily markdown/PDF digest — plus a Friday weekly strategic rollup.

## Requirements

- Python 3.12+ (uses the `py` launcher on Windows)
- An [xAI API key](https://console.x.ai)
- (Optional) SMTP credentials for email delivery — e.g. a local Proton Mail Bridge instance, or Gmail

## Setup

1. Install dependencies:
   ```
   py -3 -m pip install -r requirements.txt
   ```
   For running tests too:
   ```
   py -3 -m pip install -r requirements-dev.txt
   ```

2. Copy `.env.example` to `.env` and fill in your values:
   ```
   copy .env.example .env
   ```

   | Variable | Required | Purpose |
   |---|---|---|
   | `XAI_API_KEY` | Yes | Grok API key used for ranking and digest/rollup generation |
   | `SMTP_HOST`, `SMTP_PORT` | No | SMTP server for emailing digests (defaults to a local Proton Mail Bridge at `127.0.0.1:1025`) |
   | `SMTP_USER`, `SMTP_PASS` | No | SMTP credentials. If unset, email delivery is skipped and the digest is only saved locally |
   | `EMAIL_TO` | No | Recipient address for the daily digest and weekly rollup |
   | `LOGO_PATH` | No | Path to a logo image for the PDF header (falls back to a text wordmark) |
   | `BRAND_NAME` | No | Wordmark text shown when no `LOGO_PATH` is set (default `AI Digest`) |
   | `REPORT_DISCLAIMER` | No | Footer disclaimer text on the PDF report |
   | `OUTPUT_RETENTION_DAYS` | No | Days to keep files in `output/` before auto-pruning (default 30) |

   `.env` is gitignored — never commit it.

## Running

Run a single digest cycle (fetch → rank → summarize → save → email → notify):
```
py -3 run_digest.py
```

Output lands in `output/` as a dated markdown digest and a JSON snapshot; on Fridays a weekly rollup is also generated. On Windows, a toast notification reports success or failure.

## Scheduling (Windows Task Scheduler)

Register a recurring job that runs Mon–Fri at 07:00 (assumes the machine clock is set to CST/UTC+8 — adjust `$RunAt` in the script otherwise):
```
# Run as Administrator
.\schedule_task.ps1
```
- Run immediately: `Start-ScheduledTask -TaskName 'AI-Digest-Agent'`
- Remove: `Unregister-ScheduledTask -TaskName 'AI-Digest-Agent' -Confirm:$false`

## Testing

```
py -3 -m pytest
```
Tests marked `live` hit real external APIs/services and are excluded by default (`pytest.ini`). Run them explicitly with:
```
py -3 -m pytest -m live
```

## Project layout

- `run_digest.py` — main entry point orchestrating a full run
- `sources/` — fetchers for arXiv, lab blogs, community sources, jobs, and market data
- `ranker.py` — scores fetched items with Grok
- `digest.py` — generates the daily markdown digest
- `weekly_rollup.py` — generates the Friday strategic rollup
- `tracker.py` — seen-URL tracking, snapshots, discipline/trend deltas
- `frontier_voices.py` — tags items from OpenAI/Google/Meta-alum founders
- `email_sender.py` — renders and sends digest/rollup emails
- `notify.py` — saves digests and sends Windows notifications
- `retention.py` — prunes old files from `output/`

"""Fetchers for each data source."""

import logging
import time
from datetime import datetime, timezone, timedelta

import feedparser
import requests

from dedup_utils import normalize_title
from sources.http_utils import get_with_retry, parse_feed_with_retry

logger = logging.getLogger("ai_digest")


def _is_recent(date_str: str, days: int = 2) -> bool:
    """Return True if the parsed date is within the last N days."""
    try:
        dt = datetime(*date_str[:6], tzinfo=timezone.utc)
        return dt >= datetime.now(timezone.utc) - timedelta(days=days)
    except Exception:
        return True  # include if date unparseable


_ARXIV_API = "https://export.arxiv.org/api/query"
_ARXIV_RSS = "https://rss.arxiv.org/atom/"
_ARXIV_MIN_INTERVAL = 3.0  # arXiv API terms: no more than one request every 3s
_arxiv_last_call = 0.0


def _arxiv_get(url: str):
    """GET an arXiv URL, spacing calls at least _ARXIV_MIN_INTERVAL apart."""
    global _arxiv_last_call
    wait = _ARXIV_MIN_INTERVAL - (time.monotonic() - _arxiv_last_call)
    if wait > 0:
        time.sleep(wait)
    try:
        return requests.get(url, timeout=30)
    finally:
        _arxiv_last_call = time.monotonic()


def _arxiv_title_terms(query: str) -> list[str]:
    """Turn 'ti:foo+bar+OR+ti:baz' into ['foo bar', 'baz'] for local title matching."""
    return [t.replace("ti:", "").replace("+", " ").strip().lower() for t in query.split("+OR+")]


def _arxiv_rss_fallback(categories: list[str], query: str, max_results: int) -> list:
    """Fallback when the export API keeps failing: pull today's announcement
    feed from rss.arxiv.org (separate infrastructure from the API) and filter
    titles locally with the same terms. Empty on weekends/holidays, since
    arXiv doesn't announce then."""
    terms = _arxiv_title_terms(query)
    try:
        resp = _arxiv_get(_ARXIV_RSS + "+".join(categories))
        resp.raise_for_status()
    except Exception as e:
        logger.warning(f"arXiv RSS fallback for {categories} failed: {e}")
        return []
    entries = [
        e for e in feedparser.parse(resp.content).entries
        if e.get("arxiv_announce_type", "new") in ("new", "cross")
        and any(t in e.title.lower() for t in terms)
    ]
    return entries[:max_results]


def _arxiv_search(categories: list[str], query: str, max_results: int,
                  attempts: int = 4, base_delay: float = 5.0) -> list:
    """Query the arXiv export API, falling back to the RSS feed.

    The API throttles bursts by answering with HTTP 406/429/503 (and, since
    it moved to https-only, a 301 first for plain-http URLs). feedparser
    swallows those HTTP errors and just returns a non-bozo empty feed, so the
    old 1s/2s retry saw three silent empties and gave up. Fetching with
    requests surfaces the status, and the longer backoff (5s, 10s, 20s) gets
    past the throttle window."""
    cats = "+OR+".join(f"cat:{c}" for c in categories)
    url = (
        f"{_ARXIV_API}?search_query=({cats})+AND+({query})"
        f"&sortBy=submittedDate&sortOrder=descending&max_results={max_results}"
    )
    last_err = None
    for attempt in range(1, attempts + 1):
        retry_after = ""
        try:
            resp = _arxiv_get(url)
            if resp.status_code == 200:
                entries = feedparser.parse(resp.content).entries
                if entries:
                    return entries
                last_err = "HTTP 200 with zero entries"
            else:
                last_err = f"HTTP {resp.status_code}"
                retry_after = resp.headers.get("Retry-After", "")
        except Exception as e:
            last_err = e
        if attempt < attempts:
            delay = base_delay * (2 ** (attempt - 1))
            if retry_after.isdigit():
                delay = max(delay, min(int(retry_after), 60))
            time.sleep(delay)
    logger.warning(
        f"arXiv API query for {categories} failed after {attempts} attempts "
        f"({last_err}); falling back to RSS"
    )
    entries = _arxiv_rss_fallback(categories, query, max_results)
    logger.info(f"arXiv RSS fallback for {categories} returned {len(entries)} entries")
    return entries


def fetch_arxiv(max_results: int = 25) -> list[dict]:
    """Fetch recent AI/agents papers from arXiv cs.AI and cs.LG."""
    query = (
        "ti:agent+OR+ti:agentic+OR+ti:LLM+OR+ti:reasoning+OR+ti:multimodal"
        "+OR+ti:RAG+OR+ti:foundation+model+OR+ti:context+engineering"
        "+OR+ti:prompt+engineering+OR+ti:scaffold+OR+ti:orchestrat"
        "+OR+ti:tool+use+OR+ti:memory+OR+ti:evaluation+OR+ti:loop"
        "+OR+ti:test+time+OR+ti:inference+scaling+OR+ti:MCP"
        "+OR+ti:fine-tuning+OR+ti:alignment+OR+ti:RLHF+OR+ti:DPO+OR+ti:GRPO"
        "+OR+ti:quantization+OR+ti:efficient+inference+OR+ti:on-device"
        "+OR+ti:synthetic+data+OR+ti:red+teaming+OR+ti:benchmark"
        "+OR+ti:voice+agent+OR+ti:speech+language+model+OR+ti:audio+agent"
        "+OR+ti:coding+agent+OR+ti:software+engineering+agent+OR+ti:SWE"
        "+OR+ti:speculative+decoding+OR+ti:mixture+of+experts"
    )
    entries = _arxiv_search(['cs.AI', 'cs.LG'], query, max_results)
    results = []
    for entry in entries:
        results.append({
            "source": "arXiv",
            "title": entry.title.replace("\n", " "),
            "url": entry.link,
            "summary": entry.summary[:500],
            "date": entry.get("published", ""),
        })
    return results


def fetch_arxiv_robotics(max_results: int = 15) -> list[dict]:
    """Fetch recent embodied AI and robotics papers from arXiv cs.RO."""
    query = (
        "ti:embodied+OR+ti:humanoid+OR+ti:manipulation+OR+ti:locomotion"
        "+OR+ti:sim-to-real+OR+ti:dexterous+OR+ti:robot+learning"
        "+OR+ti:loco-manipulation+OR+ti:whole-body+control"
        "+OR+ti:vision+language+action+OR+ti:VLA+OR+ti:diffusion+policy"
        "+OR+ti:imitation+learning+OR+ti:teleoperation+OR+ti:quadruped"
        "+OR+ti:foundation+model+robot+OR+ti:generalist+robot"
    )
    entries = _arxiv_search(['cs.RO'], query, max_results)
    results = []
    for entry in entries:
        results.append({
            "source": "arXiv (Robotics)",
            "title": entry.title.replace("\n", " "),
            "url": entry.link,
            "summary": entry.summary[:500],
            "date": entry.get("published", ""),
        })
    return results


def fetch_arxiv_emerging(max_results: int = 15) -> list[dict]:
    """Fetch recent papers on topics not covered by fetch_arxiv/fetch_arxiv_robotics
    (world models, video generation, computer-use/browser agents, agent interop
    protocols). Kept as its own query rather than folded into those: appending
    these terms to the already-large existing queries pushed arXiv's search
    backend past a ~25s timeout on every request (verified live — the same
    terms in a standalone query return in ~1s), so a separate, smaller query
    is what actually keeps this reliable rather than just adding coverage."""
    query = (
        "ti:world+model+OR+ti:video+generation+OR+ti:video+diffusion"
        "+OR+ti:world+simulation+OR+ti:computer+use+OR+ti:browser+agent"
        "+OR+ti:GUI+agent+OR+ti:A2A+OR+ti:Agent2Agent+OR+ti:agent+payments"
    )
    entries = _arxiv_search(['cs.AI', 'cs.LG', 'cs.RO'], query, max_results)
    results = []
    for entry in entries:
        results.append({
            "source": "arXiv",
            "title": entry.title.replace("\n", " "),
            "url": entry.link,
            "summary": entry.summary[:500],
            "date": entry.get("published", ""),
        })
    return results


def fetch_huggingface_papers() -> list[dict]:
    """Fetch daily papers from Hugging Face via the daily_papers API."""
    try:
        resp = get_with_retry("https://huggingface.co/api/daily_papers", timeout=10)
    except Exception:
        return []

    results = []
    for entry in resp.json()[:25]:
        paper = entry.get("paper", {})
        paper_id = paper.get("id", "")
        results.append({
            "source": "HuggingFace Papers",
            "title": paper.get("title", entry.get("title", "")),
            "url": f"https://huggingface.co/papers/{paper_id}" if paper_id else "",
            "summary": paper.get("summary", entry.get("summary", ""))[:400],
            "date": paper.get("publishedAt", entry.get("publishedAt", "")),
        })
    return results



def fetch_github_trending() -> list[dict]:
    """Fetch trending AI/ML repos from GitHub via scraping-free RSS alternative."""
    feed = parse_feed_with_retry("https://mshibanami.github.io/GitHubTrendingRSS/daily/python.xml")
    ai_keywords = {
        "llm", "agent", "rag", "transformer", "diffusion", "gpt", "claude",
        "gemini", "mistral", "vision", "embedding", "fine-tun", "instruct",
        "context engineering", "prompt engineering", "harness", "scaffold",
        "orchestrat", "loop", "mcp", "tool use", "tool call", "memory",
        "evals", "evaluation", "inference", "test-time", "synthetic data",
        "robot", "embodied", "humanoid", "lora", "qlora", "quantiz",
        "vla", "speech", "voice agent", "swe", "coding agent", "edge ai",
        "alignment", "rlhf", "dpo", "grpo", "speculative", "mixture of experts",
        "world model", "video generation", "computer use", "a2a",
    }
    results = []
    for entry in feed.entries[:30]:
        title_lower = entry.title.lower()
        summary_lower = entry.get("summary", "").lower()
        if any(kw in title_lower or kw in summary_lower for kw in ai_keywords):
            results.append({
                "source": "GitHub Trending",
                "title": entry.title,
                "url": entry.link,
                "summary": entry.get("summary", "")[:400],
                "date": entry.get("published", ""),
            })
    return results[:10]


def _dedup(items: list[dict]) -> list[dict]:
    """Remove duplicates by exact URL, then by full normalized title
    (not a truncated prefix — see dedup_utils for why)."""
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    result = []
    for item in items:
        url = item.get("url", "").strip()
        title_key = normalize_title(item.get("title", ""))
        if url and url in seen_urls:
            continue
        if title_key and title_key in seen_titles:
            continue
        if url:
            seen_urls.add(url)
        if title_key:
            seen_titles.add(title_key)
        result.append(item)
    return result


def fetch_all() -> list[dict]:
    """Fetch from all sources, deduplicate, and return combined list."""
    from sources.community import fetch_alignment_forum, fetch_hackernews
    from sources.lab_blogs import fetch_lab_blogs, fetch_chinese_lab_models, fetch_chinese_robotics

    all_fetchers = [
        fetch_arxiv,
        fetch_arxiv_robotics,
        fetch_arxiv_emerging,
        fetch_huggingface_papers,
        fetch_github_trending,
        fetch_alignment_forum,
        fetch_hackernews,
        fetch_lab_blogs,
        fetch_chinese_lab_models,
        fetch_chinese_robotics,
    ]
    items = []
    for fetcher in all_fetchers:
        try:
            batch = fetcher()
            items.extend(batch)
            print(f"    {fetcher.__name__}: {len(batch)} items")
        except Exception as e:
            print(f"    [warning] {fetcher.__name__} failed: {e}")

    before = len(items)
    items = _dedup(items)
    dupes = before - len(items)
    if dupes:
        print(f"    dedup: removed {dupes} duplicate(s) ({len(items)} unique)")
    return items

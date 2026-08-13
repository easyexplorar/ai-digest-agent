"""Hacker News and Alignment Forum fetchers."""

import concurrent.futures
import time
import requests
import feedparser


HN_KEYWORDS = [
    "LLM agent", "agentic AI", "MCP server", "context engineering",
    "Claude", "Gemini", "GPT", "AI reasoning", "inference scaling",
    "AI coding", "vibe coding", "SWE-agent", "AI robotics",
    "fine-tuning", "LoRA", "local LLM", "edge AI", "quantization",
    "AI alignment", "prompt injection", "agent security",
    "embodied AI", "humanoid robot", "voice AI", "DeepSeek", "Qwen",
]

HEADERS = {"User-Agent": "AI-Digest-Agent/1.0 (research digest tool)"}
_session = requests.Session()
_session.headers.update(HEADERS)

ALIGNMENT_FEEDS = [
    ("Alignment Forum", "https://www.alignmentforum.org/feed.xml"),
    ("LessWrong",       "https://www.lesswrong.com/feed.xml"),
]


def fetch_alignment_forum() -> list[dict]:
    """Fetch recent posts from Alignment Forum and LessWrong."""
    results = []
    for source_name, feed_url in ALIGNMENT_FEEDS:
        try:
            feed = feedparser.parse(feed_url, request_headers=HEADERS)
            for entry in feed.entries[:5]:
                results.append({
                    "source": source_name,
                    "title": entry.get("title", ""),
                    "url": entry.get("link", ""),
                    "summary": entry.get("summary", "")[:400],
                    "date": entry.get("published", ""),
                })
        except Exception:
            continue
    return results


def _search_hn_keyword(kw: str, cutoff: int) -> list[tuple[dict, int]]:
    """Search one keyword; returns (item, points) pairs so the caller can
    sort by points without re-parsing it back out of the summary text."""
    out = []
    try:
        resp = _session.get(
            "https://hn.algolia.com/api/v1/search_by_date",
            params={
                "query": kw,
                "tags": "story",
                "hitsPerPage": 10,
                "numericFilters": f"created_at_i>{cutoff}",
            },
            timeout=10,
        )
        resp.raise_for_status()
        for hit in resp.json().get("hits", []):
            points = hit.get("points", 0) or 0
            if points < 5:
                continue
            url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit['objectID']}"
            out.append((
                {
                    "source": "Hacker News",
                    "title": hit.get("title", ""),
                    "url": url,
                    "summary": (
                        f"Points: {points} | "
                        f"Comments: {hit.get('num_comments', 0)}"
                    ),
                    "date": hit.get("created_at", ""),
                },
                points,
            ))
    except Exception:
        pass
    return out


def fetch_hackernews() -> list[dict]:
    """Search HN for each keyword in HN_KEYWORDS concurrently — previously
    ~25 sequential requests, one per keyword."""
    cutoff = int(time.time()) - 48 * 3600
    seen: set[str] = set()
    scored: list[tuple[dict, int]] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(_search_hn_keyword, kw, cutoff) for kw in HN_KEYWORDS]
        for future in concurrent.futures.as_completed(futures):
            for item, points in future.result():
                if item["url"] not in seen:
                    seen.add(item["url"])
                    scored.append((item, points))

    scored.sort(key=lambda pair: pair[1], reverse=True)
    return [item for item, _ in scored[:15]]

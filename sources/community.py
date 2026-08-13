"""Hacker News and Alignment Forum fetchers."""

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


def fetch_hackernews() -> list[dict]:
    cutoff = int(time.time()) - 48 * 3600
    results = []
    seen: set[str] = set()

    for kw in HN_KEYWORDS:
        try:
            resp = requests.get(
                "https://hn.algolia.com/api/v1/search_by_date",
                params={
                    "query": kw,
                    "tags": "story",
                    "hitsPerPage": 10,
                    "numericFilters": f"created_at_i>{cutoff}",
                },
                headers=HEADERS,
                timeout=10,
            )
            resp.raise_for_status()
            for hit in resp.json().get("hits", []):
                points = hit.get("points", 0) or 0
                if points < 5:
                    continue
                url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit['objectID']}"
                if url not in seen:
                    seen.add(url)
                    results.append({
                        "source": "Hacker News",
                        "title": hit.get("title", ""),
                        "url": url,
                        "summary": (
                            f"Points: {points} | "
                            f"Comments: {hit.get('num_comments', 0)}"
                        ),
                        "date": hit.get("created_at", ""),
                    })
        except Exception:
            continue

    return sorted(results, key=lambda x: int(x["summary"].split("|")[0].split(":")[1].strip()),
                  reverse=True)[:15]

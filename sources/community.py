"""Hacker News and Alignment Forum fetchers."""

import concurrent.futures
import time
import requests

from sources.http_utils import get_with_retry, parse_feed_with_retry


HN_KEYWORDS = [
    "LLM agent", "agentic AI", "MCP server", "context engineering",
    "Claude", "Gemini", "GPT", "AI reasoning", "inference scaling",
    "AI coding", "vibe coding", "SWE-agent", "AI robotics",
    "fine-tuning", "LoRA", "local LLM", "edge AI", "quantization",
    "AI alignment", "prompt injection", "agent security",
    "embodied AI", "humanoid robot", "voice AI", "DeepSeek", "Qwen",
    # Lab/company names, as distinct from product names above — news
    # phrased around the company (funding, org changes, policy) doesn't
    # always mention the product name, so both need their own search.
    "Anthropic", "OpenAI", "xAI", "Grok", "Meta AI", "Llama",
    "Mistral AI", "Cohere", "Perplexity AI",
    # Frontier-lab founders (OpenAI/Google/Meta alumni now running their own
    # labs) — most of these labs have no blog/RSS feed of their own yet, so
    # HN discussion is the main way their news gets caught at all.
    "Safe Superintelligence", "Ilya Sutskever", "AMI Labs", "Yann LeCun",
    "Discovery Loop", "Jeff Dean", "Thinking Machines Lab", "Mira Murati",
    "Andrew Ng", "DeepLearning.AI",
    # World models / video generation — no coverage anywhere else (not a
    # paper-title convention arXiv's search handles well, so HN carries it).
    "world model", "video generation",
    # Agent interop protocols and computer/browser-control agents — parallel
    # tracks to MCP that weren't caught by the existing agent keywords.
    "Agent2Agent", "agent payments protocol", "computer use agent",
    "browser agent",
    # Custom AI silicon beyond NVIDIA.
    "Trainium", "TPU chip", "Cerebras", "Groq chip", "custom AI chip",
    # AI compute/energy infrastructure — no keyword or source covered this
    # at all despite it being a constant 2025-2026 storyline.
    "AI data center", "AI power deal", "AI compute buildout",
    # Funding/M&A — not paper- or repo-shaped, so this is HN-only.
    "AI funding round", "AI startup raises", "AI acquisition",
    # Policy/regulation — HN-only for now rather than a dedicated feed,
    # since HN's coverage skews US/EU headline news rather than being
    # comprehensive; revisit with a real policy feed if this proves thin.
    "AI regulation", "AI Act", "AI executive order",
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
            feed = parse_feed_with_retry(feed_url, request_headers=HEADERS)
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
        resp = get_with_retry(
            "https://hn.algolia.com/api/v1/search_by_date",
            session=_session,
            params={
                "query": kw,
                "tags": "story",
                "hitsPerPage": 10,
                "numericFilters": f"created_at_i>{cutoff}",
            },
            timeout=10,
        )
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

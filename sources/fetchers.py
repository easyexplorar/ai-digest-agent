"""Fetchers for each data source."""

from datetime import datetime, timezone, timedelta

from dedup_utils import normalize_title
from sources.http_utils import get_with_retry, parse_feed_with_retry


def _is_recent(date_str: str, days: int = 2) -> bool:
    """Return True if the parsed date is within the last N days."""
    try:
        dt = datetime(*date_str[:6], tzinfo=timezone.utc)
        return dt >= datetime.now(timezone.utc) - timedelta(days=days)
    except Exception:
        return True  # include if date unparseable


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
    url = (
        f"http://export.arxiv.org/api/query"
        f"?search_query=(cat:cs.AI+OR+cat:cs.LG)+AND+({query})"
        f"&sortBy=submittedDate&sortOrder=descending"
        f"&max_results={max_results}"
    )
    feed = parse_feed_with_retry(url)
    results = []
    for entry in feed.entries:
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
    url = (
        f"http://export.arxiv.org/api/query"
        f"?search_query=cat:cs.RO+AND+({query})"
        f"&sortBy=submittedDate&sortOrder=descending"
        f"&max_results={max_results}"
    )
    feed = parse_feed_with_retry(url)
    results = []
    for entry in feed.entries:
        results.append({
            "source": "arXiv (Robotics)",
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

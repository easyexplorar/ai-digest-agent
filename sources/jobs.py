"""AI industry job posting fetcher using Greenhouse and Lever public APIs."""

from datetime import datetime, timezone, timedelta

from sources.http_utils import get_with_retry

HEADERS = {"User-Agent": "AI-Digest-Agent/1.0 (research digest tool)"}

# Roles that are clearly AI/ML-relevant
AI_ROLE_KEYWORDS = {
    "machine learning", "ml engineer", "research scientist", "ai researcher",
    "llm", "foundation model", "applied scientist", "nlp", "computer vision",
    "robotics", "reinforcement learning", "ai safety", "alignment",
    "multimodal", "inference engineer", "data scientist", "deep learning",
    "generative ai", "language model", "prompt", "agent", "rl ",
}

# (greenhouse_slug, display_name)
GREENHOUSE_COMPANIES = [
    ("anthropic",       "Anthropic"),
    ("cohere",          "Cohere"),
    ("scaleai",         "Scale AI"),
    ("together",        "Together AI"),
    ("adept",           "Adept AI"),
    ("descript",        "Descript"),
    ("huggingface",     "Hugging Face"),
    ("openai",          "OpenAI"),
]

# (lever_slug, display_name)
LEVER_COMPANIES = [
    ("mistral",         "Mistral AI"),
    ("perplexityai",    "Perplexity AI"),
    ("replit",          "Replit"),
    ("imbue",           "Imbue"),
]

_WEEK_AGO = datetime.now(timezone.utc) - timedelta(days=7)


def _is_ai_role(title: str) -> bool:
    t = title.lower()
    return any(kw in t for kw in AI_ROLE_KEYWORDS)


def _fetch_greenhouse(slug: str, company: str) -> list[dict]:
    try:
        resp = get_with_retry(
            f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
            params={"content": "false"},
            headers=HEADERS,
            timeout=10,
        )
        jobs = []
        for j in resp.json().get("jobs", []):
            title = j.get("title", "")
            if not _is_ai_role(title):
                continue
            updated_at = j.get("updated_at", "")
            try:
                dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                if dt < _WEEK_AGO:
                    continue
            except Exception:
                pass
            loc = j.get("location", {}).get("name", "")
            jobs.append({
                "company": company,
                "title": title,
                "location": loc,
                "url": j.get("absolute_url", ""),
                "date": updated_at,
                "source": "Greenhouse",
            })
        return jobs
    except Exception:
        return []


def _fetch_lever(slug: str, company: str) -> list[dict]:
    try:
        resp = get_with_retry(
            f"https://api.lever.co/v0/postings/{slug}",
            params={"mode": "json", "limit": 50},
            headers=HEADERS,
            timeout=10,
        )
        jobs = []
        for j in resp.json():
            title = j.get("text", "")
            if not _is_ai_role(title):
                continue
            created_at = j.get("createdAt", 0)
            try:
                dt = datetime.fromtimestamp(created_at / 1000, tz=timezone.utc)
                if dt < _WEEK_AGO:
                    continue
            except Exception:
                pass
            loc = j.get("categories", {}).get("location", "")
            jobs.append({
                "company": company,
                "title": title,
                "location": loc,
                "url": j.get("hostedUrl", ""),
                "date": str(created_at),
                "source": "Lever",
            })
        return jobs
    except Exception:
        return []


def fetch_ai_jobs() -> list[dict]:
    """Return AI-relevant job postings from major labs posted in the last 7 days."""
    results = []
    for slug, name in GREENHOUSE_COMPANIES:
        results.extend(_fetch_greenhouse(slug, name))
    for slug, name in LEVER_COMPANIES:
        results.extend(_fetch_lever(slug, name))
    return results

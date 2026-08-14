"""AI lab blog RSS fetchers — Western labs and Chinese labs via HuggingFace org API."""

import concurrent.futures
import requests

from sources.http_utils import get_with_retry, parse_feed_with_retry

HEADERS = {"User-Agent": "AI-Digest-Agent/1.0 (research digest tool)"}
_session = requests.Session()
_session.headers.update(HEADERS)

# (display name, RSS/Atom feed URL)
WESTERN_LAB_FEEDS = [
    ("OpenAI",               "https://openai.com/blog/rss.xml"),
    ("Google DeepMind",      "https://deepmind.google/blog/rss.xml"),
    ("Meta Engineering",     "https://engineering.fb.com/feed/"),
    ("NVIDIA Research",      "https://blogs.nvidia.com/feed/"),
    ("Apple ML Research",    "https://machinelearning.apple.com/rss.xml"),
    ("Hugging Face",         "https://huggingface.co/blog/feed.xml"),
    ("Microsoft Research",   "https://www.microsoft.com/en-us/research/feed/"),
    # Anthropic doesn't publish an RSS/Atom feed for anthropic.com/news
    # (verified live — no feed at any common path, none advertised via
    # <link rel="alternate"> on the site). Their Claude Code release notes
    # are the closest available substitute: real GitHub Atom feed, and
    # directly relevant to this digest's AI-native-software-engineering
    # and agent-framework coverage.
    ("Claude Code (Anthropic)", "https://github.com/anthropics/claude-code/releases.atom"),
]

# Chinese labs tracked via their HuggingFace organisation model releases
# (display name, HuggingFace org slug)
CHINESE_LAB_HF_ORGS = [
    ("DeepSeek",                   "deepseek-ai"),
    ("Qwen (Alibaba)",             "Qwen"),
    ("InternLM (Shanghai AI Lab)", "internlm"),
    ("Hunyuan (Tencent)",          "tencent"),
    ("Doubao (ByteDance)",         "bytedance-research"),
    ("Kimi (Moonshot AI)",         "moonshotai"),
    ("Zhipu AI",                   "THUDM"),
    ("Baichuan AI",                "baichuan-inc"),
]

# Chinese robotics and embodied AI labs on HuggingFace
CHINESE_ROBOTICS_HF_ORGS = [
    ("Unitree Robotics",           "unitreerobotics"),
    ("AgiBot",                     "agibot-world"),
    ("RoboticsTHU (Tsinghua)",     "RoboticsTHU"),
    ("OpenDriveLab",               "OpenDriveLab"),
]


def fetch_lab_blogs() -> list[dict]:
    """Fetch recent posts from Western AI lab RSS feeds."""
    results = []
    for lab_name, feed_url in WESTERN_LAB_FEEDS:
        try:
            feed = parse_feed_with_retry(feed_url, request_headers=HEADERS)
            for entry in feed.entries[:3]:
                results.append({
                    "source": f"{lab_name} Blog",
                    "title": entry.get("title", "").strip(),
                    "url": entry.get("link", ""),
                    "summary": entry.get("summary", "")[:400],
                    # GitHub release Atom feeds set "updated", not "published"
                    "date": entry.get("published", entry.get("updated", "")),
                })
        except Exception:
            continue
    return results


def _format_param_count(safetensors: dict | None) -> str:
    """Extract total parameter count from safetensors metadata and format it."""
    if not safetensors:
        return ""
    total = safetensors.get("total", 0)
    if not total:
        params = safetensors.get("parameters", {})
        total = sum(params.values()) if params else 0
    if total <= 0:
        return ""
    if total >= 1_000_000_000:
        return f"{total / 1_000_000_000:.1f}B"
    if total >= 1_000_000:
        return f"{total / 1_000_000:.0f}M"
    return f"{total / 1_000:.0f}K"


def _fetch_model_detail(model_id: str) -> dict:
    """Fetch license and parameter size from the individual model endpoint."""
    try:
        resp = get_with_retry(
            f"https://huggingface.co/api/models/{model_id}",
            session=_session,
            timeout=8,
        )
        data = resp.json()
        card = data.get("cardData") or {}
        license_info = card.get("license", "")
        if isinstance(license_info, list):
            license_info = ", ".join(license_info)
        param_size = _format_param_count(data.get("safetensors"))
        return {"license": license_info, "param_size": param_size}
    except Exception:
        return {"license": "", "param_size": ""}


def _fetch_hf_org_releases(org_list: list[tuple], source_tag: str) -> list[dict]:
    """Generic fetcher for recent HuggingFace org model/dataset releases."""
    org_models: list[tuple[str, dict]] = []
    for lab_name, org_id in org_list:
        try:
            resp = get_with_retry(
                "https://huggingface.co/api/models",
                session=_session,
                params={
                    "author": org_id,
                    "sort": "lastModified",
                    "direction": -1,
                    "limit": 5,
                },
                timeout=10,
            )
            for model in resp.json():
                org_models.append((lab_name, model))
        except Exception:
            continue

    if not org_models:
        return []

    # Per-model license/param-size detail calls (up to 5 per org × N orgs)
    # were previously sequential — fetch them concurrently instead.
    details: dict[int, dict] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_idx = {
            executor.submit(_fetch_model_detail, model.get("modelId", "")): i
            for i, (_, model) in enumerate(org_models)
        }
        for future in concurrent.futures.as_completed(future_to_idx):
            details[future_to_idx[future]] = future.result()

    results = []
    for i, (lab_name, model) in enumerate(org_models):
        model_id = model.get("modelId", "")
        tags = model.get("tags", [])
        detail = details.get(i, {"license": "", "param_size": ""})
        license_info = detail["license"]
        param_size = detail["param_size"]

        meta_parts = [f"Tags: {', '.join(tags[:12])}"]
        if license_info:
            meta_parts.append(f"License: {license_info}")
        if param_size:
            meta_parts.append(f"Size: {param_size}")

        results.append({
            "source": f"{lab_name} ({source_tag})",
            "title": f"Model release: {model_id}",
            "url": f"https://huggingface.co/{model_id}",
            "summary": " | ".join(meta_parts),
            "date": model.get("lastModified", ""),
            "license": license_info,
            "param_size": param_size,
        })
    return results


def fetch_chinese_lab_models() -> list[dict]:
    """Fetch recent model releases from Chinese AI labs via HuggingFace org API."""
    return _fetch_hf_org_releases(CHINESE_LAB_HF_ORGS, "HuggingFace")


def fetch_chinese_robotics() -> list[dict]:
    """Fetch recent releases from Chinese robotics and embodied AI labs on HuggingFace."""
    return _fetch_hf_org_releases(CHINESE_ROBOTICS_HF_ORGS, "Robotics HF")

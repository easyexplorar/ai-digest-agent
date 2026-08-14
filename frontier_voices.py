"""Tags fetched items that mention a tracked frontier-lab founder or their
company, so the digest's Frontier Voices section can surface them from the
*full* ranked list rather than only whatever makes the overall top 10 (see
tracker.format_china_context — same failure mode, same fix shape).

Most of these labs don't publish an RSS/Atom feed yet (verified live,
2026-08-14): Safe Superintelligence is famously in stealth, AMI Labs and
Discovery Loop are brand-new startups, and DeepLearning.AI's "The Batch"
has no discoverable feed either. Thinking Machines Lab is the one
exception with a real blog feed. For the rest, coverage comes from
whatever surfaces via the Hacker News keyword search (see
sources/community.py's HN_KEYWORDS) or any other source that happens to
mention them — this tagging step is what finds those mentions regardless
of which fetcher they came from.
"""

# Sources that are always about one specific tracked lab, no keyword
# matching needed.
FRONTIER_SOURCES = {
    "Thinking Machines Lab Blog": "Thinking Machines Lab (Mira Murati)",
}

# Lowercase keyword -> label. Checked against "{title} {summary}".lower()
# for every item regardless of source (HN, arXiv, GitHub Trending, etc.).
FRONTIER_KEYWORDS = {
    "safe superintelligence": "Safe Superintelligence (Ilya Sutskever)",
    "ilya sutskever":         "Safe Superintelligence (Ilya Sutskever)",
    "yann lecun":              "AMI Labs (Yann LeCun)",
    "ami labs":                "AMI Labs (Yann LeCun)",
    "advanced machine intelligence": "AMI Labs (Yann LeCun)",
    "discovery loop":          "Discovery Loop (Jeff Dean)",
    "jeff dean":                "Discovery Loop (Jeff Dean)",
    "thinking machines":       "Thinking Machines Lab (Mira Murati)",
    "mira murati":              "Thinking Machines Lab (Mira Murati)",
    "andrew ng":                "DeepLearning.AI (Andrew Ng)",
    "deeplearning.ai":          "DeepLearning.AI (Andrew Ng)",
}


def tag_frontier_voices(items: list[dict]) -> list[dict]:
    """Mutates items in place, adding a "frontier_voice" label to any item
    naming a tracked founder or lab in its source, title, or summary.
    Returns the same list for convenience."""
    for item in items:
        label = FRONTIER_SOURCES.get(item.get("source", ""))
        if not label:
            text = f"{item.get('title', '')} {item.get('summary', '')}".lower()
            for kw, lbl in FRONTIER_KEYWORDS.items():
                if kw in text:
                    label = lbl
                    break
        if label:
            item["frontier_voice"] = label
    return items

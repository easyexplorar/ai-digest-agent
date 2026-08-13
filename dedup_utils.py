"""Shared title normalization for cross-source and cross-day dedup.

Used to compare *full* normalized titles instead of a truncated prefix, so
two items that happen to share the same opening words but diverge later are
no longer wrongly treated as duplicates.

Deliberately conservative (exact match, not fuzzy similarity): an earlier
attempt using difflib similarity ratios produced false positives on
"Model release: org/Name" titles, where genuinely different model variants
(e.g. "UnifoLM-VLA-Base" vs "UnifoLM-VLA-Libero") score 0.85+ similar purely
from shared naming conventions. Exact match on the normalized string avoids
that failure mode entirely.
"""

import re

_PUNCT_RE = re.compile(r"[^\w\s]")
_WS_RE = re.compile(r"\s+")


def normalize_title(title: str) -> str:
    t = title.lower()
    t = _PUNCT_RE.sub(" ", t)
    t = _WS_RE.sub(" ", t).strip()
    return t

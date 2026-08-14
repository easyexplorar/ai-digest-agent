"""Prunes old digest artifacts from output/ so it doesn't grow unbounded.

Deletion is based on file mtime, not filename parsing, so it applies
uniformly across the different naming schemes in output/ (digest_*.md,
snapshot_*.json, urls_*.json, weekly_*.md). The default window (30 days)
is well beyond the 3-5 day lookback tracker.py needs for trend/dedup, so
pruning never removes a file the pipeline still reads.
"""

import os
import time
from pathlib import Path

PRUNE_PATTERNS = ("digest_*.md", "snapshot_*.json", "urls_*.json", "weekly_*.md")


def prune_output(output_dir: str = "output", retention_days: int | None = None, logger=None) -> list[Path]:
    """Delete tracked digest artifacts older than retention_days. Returns deleted paths."""
    if retention_days is None:
        retention_days = int(os.getenv("OUTPUT_RETENTION_DAYS", "30"))

    out = Path(output_dir)
    if not out.exists():
        return []

    cutoff = time.time() - retention_days * 86400
    deleted = []
    for pattern in PRUNE_PATTERNS:
        for path in out.glob(pattern):
            if path.stat().st_mtime < cutoff:
                path.unlink()
                deleted.append(path)

    if deleted and logger:
        logger.info(f"Pruned {len(deleted)} output file(s) older than {retention_days} days.")

    return deleted

"""Shared retry/backoff wrapper for xAI (Grok) API calls.

The Grok calls in ranker.py, digest.py, and weekly_rollup.py are each a
single unattended attempt today — a transient network blip or rate limit
kills that chunk/section outright. This gives them a shared retry policy.
"""

import logging
import time

logger = logging.getLogger("ai_digest")


def generate_content_with_retry(client, attempts: int = 3, base_delay: float = 2.0, **kwargs):
    """Call client.chat.completions.create, retrying transient failures with
    exponential backoff (base_delay, base_delay*2, base_delay*4, ...)."""
    for attempt in range(1, attempts + 1):
        try:
            return client.chat.completions.create(**kwargs)
        except Exception as e:
            if attempt == attempts:
                logger.error(f"Grok call failed after {attempts} attempts: {e}")
                raise
            delay = base_delay * (2 ** (attempt - 1))
            logger.warning(f"Grok call attempt {attempt}/{attempts} failed ({e}); retrying in {delay:.0f}s")
            time.sleep(delay)

"""Shared retry/backoff wrapper for xAI (Grok) API calls.

The Grok calls in ranker.py, digest.py, and weekly_rollup.py are each a
single unattended attempt today — a transient network blip or rate limit
kills that chunk/section outright. This gives them a shared retry policy.

Calls are streamed: a non-streamed request sits silent until the whole
completion is ready, and on this machine's network path (VPN tunnel) a
connection idle for ~10s+ gets dropped — "Server disconnected without
sending a response". Streaming keeps bytes flowing so long generations
survive.
"""

import logging
import time
from types import SimpleNamespace

logger = logging.getLogger("ai_digest")


def _collect_stream(stream):
    """Join streamed chunks into an object shaped like a non-streamed
    response, so callers can keep using response.choices[0].message.content."""
    parts = []
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            parts.append(chunk.choices[0].delta.content)
    message = SimpleNamespace(content="".join(parts))
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def generate_content_with_retry(client, attempts: int = 4, base_delay: float = 5.0, **kwargs):
    """Call client.chat.completions.create (streamed), retrying transient
    failures with exponential backoff (base_delay, base_delay*2, ...)."""
    for attempt in range(1, attempts + 1):
        try:
            return _collect_stream(client.chat.completions.create(stream=True, **kwargs))
        except Exception as e:
            if attempt == attempts:
                logger.error(f"Grok call failed after {attempts} attempts: {e}")
                raise
            delay = base_delay * (2 ** (attempt - 1))
            logger.warning(f"Grok call attempt {attempt}/{attempts} failed ({e}); retrying in {delay:.0f}s")
            time.sleep(delay)

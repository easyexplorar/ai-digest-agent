"""Shared retry/backoff wrapper for outbound HTTP calls made by the source
fetchers (fetchers.py, community.py, lab_blogs.py, jobs.py).

Mirrors grok_utils.generate_content_with_retry: a transient network blip
during an unattended run previously killed that fetcher's entire result
outright (each site wrapped its own single attempt in a bare except). This
gives them a shared retry policy instead of each rolling its own.
"""

import logging
import time

import feedparser
import requests

logger = logging.getLogger("ai_digest")


def get_with_retry(url: str, attempts: int = 3, base_delay: float = 1.0, session=None, **kwargs):
    """GET a URL, retrying transient failures with exponential backoff
    (base_delay, base_delay*2, ...). Raises the last exception if every
    attempt fails — callers keep their own try/except around this so one
    failing endpoint doesn't take down the rest of that fetcher."""
    getter = session.get if session is not None else requests.get
    for attempt in range(1, attempts + 1):
        try:
            resp = getter(url, **kwargs)
            resp.raise_for_status()
            return resp
        except Exception as e:
            if attempt == attempts:
                logger.warning(f"GET {url} failed after {attempts} attempts: {e}")
                raise
            delay = base_delay * (2 ** (attempt - 1))
            time.sleep(delay)


def parse_feed_with_retry(url: str, request_headers: dict | None = None,
                           attempts: int = 3, base_delay: float = 1.0):
    """Parse an RSS/Atom feed, retrying if the fetch came back empty due to
    a network failure. feedparser doesn't raise on network errors — it sets
    feed.bozo and returns zero entries — so that combination (no entries,
    bozo set) is what triggers a retry. A feed that's merely not
    well-formed XML but still yielded entries is left alone; retrying that
    wouldn't help and would just add latency."""
    feed = None
    for attempt in range(1, attempts + 1):
        feed = feedparser.parse(url, request_headers=request_headers)
        if feed.entries or not feed.bozo:
            return feed
        if attempt == attempts:
            logger.warning(
                f"Feed parse for {url} returned no entries after {attempts} attempts: "
                f"{feed.get('bozo_exception')}"
            )
            return feed
        time.sleep(base_delay * (2 ** (attempt - 1)))
    return feed

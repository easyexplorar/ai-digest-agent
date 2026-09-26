import pytest

import sources.fetchers as fetchers


API_FEED = b"""<?xml version='1.0' encoding='UTF-8'?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry><title>Humanoid Walking</title><id>http://arxiv.org/abs/2609.00001v1</id>
    <link href="https://arxiv.org/abs/2609.00001v1"/><summary>s</summary></entry>
</feed>"""

EMPTY_FEED = b"""<?xml version='1.0' encoding='UTF-8'?>
<feed xmlns="http://www.w3.org/2005/Atom"></feed>"""

RSS_FEED = b"""<?xml version='1.0' encoding='UTF-8'?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry><title>A Humanoid Loco-Manipulation Policy</title>
    <link href="https://arxiv.org/abs/2609.00002"/><summary>s</summary>
    <arxiv:announce_type>new</arxiv:announce_type></entry>
  <entry><title>Unrelated SLAM Paper</title>
    <link href="https://arxiv.org/abs/2609.00003"/><summary>s</summary>
    <arxiv:announce_type>new</arxiv:announce_type></entry>
  <entry><title>Old Humanoid Paper, Revised</title>
    <link href="https://arxiv.org/abs/2601.00004"/><summary>s</summary>
    <arxiv:announce_type>replace</arxiv:announce_type></entry>
</feed>"""


class FakeResp:
    def __init__(self, status, content=b"", headers=None):
        self.status_code = status
        self.content = content
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


@pytest.fixture
def fake_get(monkeypatch):
    """Replace _arxiv_get with a scripted sequence of responses; no sleeping."""
    calls = []

    def install(responses):
        it = iter(responses)

        def _get(url):
            calls.append(url)
            return next(it)

        monkeypatch.setattr(fetchers, "_arxiv_get", _get)
        return calls

    monkeypatch.setattr(fetchers.time, "sleep", lambda s: None)
    return install


def test_title_terms_from_query():
    assert fetchers._arxiv_title_terms("ti:humanoid+OR+ti:robot+learning") == [
        "humanoid", "robot learning"]


def test_retries_past_throttle_status(fake_get):
    calls = fake_get([FakeResp(406), FakeResp(200, EMPTY_FEED), FakeResp(200, API_FEED)])
    entries = fetchers._arxiv_search(["cs.RO"], "ti:humanoid", 5)
    assert [e.title for e in entries] == ["Humanoid Walking"]
    assert len(calls) == 3
    assert calls[0].startswith("https://export.arxiv.org/api/query?search_query=(cat:cs.RO)+AND+(ti:humanoid)")


def test_falls_back_to_rss_and_filters_titles(fake_get):
    calls = fake_get([FakeResp(503)] * 4 + [FakeResp(200, RSS_FEED)])
    entries = fetchers._arxiv_search(["cs.RO"], "ti:humanoid+OR+ti:loco-manipulation", 5)
    assert [e.title for e in entries] == ["A Humanoid Loco-Manipulation Policy"]
    assert calls[-1] == "https://rss.arxiv.org/atom/cs.RO"


def test_fallback_failure_returns_empty(fake_get):
    fake_get([FakeResp(503)] * 4 + [FakeResp(500)])
    assert fetchers._arxiv_search(["cs.RO"], "ti:humanoid", 5) == []


@pytest.mark.live
def test_live_arxiv_fetchers_return_results():
    assert fetchers.fetch_arxiv()
    assert fetchers.fetch_arxiv_robotics()
    assert fetchers.fetch_arxiv_emerging()

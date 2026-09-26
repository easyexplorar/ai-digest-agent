import pytest

import sources.fetchers as fetchers


LISTING = """<ul class="list-papers list-group list-group-flush">
     <li class="item reproducibility ">
        <h4><a class="paper-data-bs-title darkblue" href="https://openreview.net/pdf?id=abc123"><b>Concept   Sliders
        for Diffusion &amp; Video</b></a></h4>
        <p><i>Maximilian N\u00e4gele, Jane Doe</i>, September 2026  <br>
            [<a href="https://openreview.net/forum?id=abc123">openreview</a>] [<a href="/tmlr/papers/bib/abc123.bib">bib</a>]
             <br> Certifications:
                 <a href="#" class="badge text-bg-success" data-bs-toggle="tooltip">Reproducibility</a>
     </li>
     <li class="item ">
        <h4><a class="paper-data-bs-title darkblue" href="https://openreview.net/pdf?id=def456"><b>Solo Paper</b></a></h4>
        <p><i>Solo Author</i>, August 2026  <br>
            [<a href="https://openreview.net/forum?id=def456">openreview</a>]
     </li>
</ul>"""


class FakeResp:
    def __init__(self, text):
        self.text = text
        self.encoding = None


def test_parses_listing(monkeypatch):
    monkeypatch.setattr(fetchers, "get_with_retry", lambda url, **kw: FakeResp(LISTING))
    items = fetchers.fetch_tmlr()
    assert items == [
        {
            "source": "TMLR",
            "title": "Concept Sliders for Diffusion & Video",
            "url": "https://openreview.net/forum?id=abc123",
            "summary": "Peer-reviewed TMLR paper by Maximilian N\u00e4gele et al.; certifications: Reproducibility",
            "date": "September 2026",
        },
        {
            "source": "TMLR",
            "title": "Solo Paper",
            "url": "https://openreview.net/forum?id=def456",
            "summary": "Peer-reviewed TMLR paper by Solo Author",
            "date": "August 2026",
        },
    ]


def test_fetch_failure_returns_empty(monkeypatch):
    def boom(url, **kw):
        raise RuntimeError("down")
    monkeypatch.setattr(fetchers, "get_with_retry", boom)
    assert fetchers.fetch_tmlr() == []


@pytest.mark.live
def test_live_tmlr_returns_results():
    assert fetchers.fetch_tmlr()

from types import SimpleNamespace

from digest import _LABELLED_SECTIONS, _bold_bullet_labels, generate_digest


def test_bolds_plain_labels_in_new_sections():
    text = (
        "## Capital Markets Lens\n\n"
        "Stocks were mixed.\n\n"
        "- Cloud and software vendors: Demand holds up.\n\n"
        "## Skills Gap: What to Learn\n\n"
        "- Designing audit logs that resist tampering: Security teams should learn this. "
        "*Start by:* Reviewing logging features.\n"
    )
    out = _bold_bullet_labels(text)
    assert "- **Cloud and software vendors:** Demand holds up." in out
    assert "- **Designing audit logs that resist tampering:** Security teams" in out
    assert "*Start by:* Reviewing" in out  # inline italic label left alone


def test_leaves_already_bold_labels_alone():
    text = "## Capital Markets Lens\n\n- **Chip makers:** Up today.\n"
    assert _bold_bullet_labels(text) == text


def test_only_touches_labelled_sections():
    text = "## On Our Radar This Week\n\n- Watch this: something.\n"
    assert _bold_bullet_labels(text) == text


def test_skills_gap_stays_a_labelled_section():
    assert "## Skills Gap: What to Learn" in _LABELLED_SECTIONS


_ITEM = {
    "score": 8,
    "discipline": "Model Release",
    "source": "Example Lab",
    "title": "A plain-English story",
    "url": "https://example.com/story",
    "date": "2026-10-11",
    "summary": "Something happened.",
    "reason": "It matters.",
}


def _capture_prompt(monkeypatch):
    captured = {}

    def fake_generate(client, **kwargs):
        captured["prompt"] = kwargs["messages"][0]["content"]
        message = SimpleNamespace(content="## Skills Gap: What to Learn\n\nDone.")
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    monkeypatch.setattr("digest.generate_content_with_retry", fake_generate)
    monkeypatch.setattr("digest.OpenAI", lambda **kwargs: object())
    return captured


def test_generate_digest_fills_jobs_context(monkeypatch):
    captured = _capture_prompt(monkeypatch)
    line = "Anthropic — Research Scientist (San Francisco) — https://example.com/job"
    generate_digest([_ITEM], api_key="test-key", jobs_context=line)
    assert line in captured["prompt"]
    assert "{jobs_context}" not in captured["prompt"]
    assert "## Skills Gap: What to Learn" in captured["prompt"]


def test_generate_digest_empty_jobs_context_uses_fallback(monkeypatch):
    captured = _capture_prompt(monkeypatch)
    generate_digest([_ITEM], api_key="test-key", jobs_context="")
    assert "No recent AI job postings available." in captured["prompt"]
    assert "{jobs_context}" not in captured["prompt"]

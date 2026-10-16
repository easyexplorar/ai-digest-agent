from digest import _LABELLED_SECTIONS, _bold_bullet_labels


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


def test_prompt_has_numbers_section_before_big_picture():
    from digest import DIGEST_PROMPT
    from tracker import NUMBERS_SECTION
    assert NUMBERS_SECTION in DIGEST_PROMPT
    assert DIGEST_PROMPT.index(NUMBERS_SECTION) < DIGEST_PROMPT.index("## The Big Picture")
    assert "{recent_concepts}" in DIGEST_PROMPT


def test_drops_unfilled_numbers_section_with_header():
    from digest import _drop_empty_numbers_section
    text = (
        "## Skills Gap: What to Learn\n\n- **Skill:** text\n\n"
        "## The Numbers Behind the News\nNo headline numbers worth unpacking today.\n\n"
        "## The Big Picture\n\nSummary.\n"
    )
    out = _drop_empty_numbers_section(text)
    assert "Numbers Behind" not in out
    assert "## Skills Gap" in out and "## The Big Picture\n\nSummary." in out


def test_keeps_filled_numbers_section():
    from digest import _drop_empty_numbers_section
    text = (
        "## The Numbers Behind the News\n\n**Concept:** Base rates\n\n"
        "**The number:** 95%.\n\n## The Big Picture\n\nSummary.\n"
    )
    assert _drop_empty_numbers_section(text) == text

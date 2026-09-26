from digest import _bold_bullet_labels


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

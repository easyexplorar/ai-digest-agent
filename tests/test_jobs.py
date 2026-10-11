from sources.jobs import format_jobs_context


def test_format_jobs_context_empty():
    assert format_jobs_context([]) == "No recent AI job postings available."


def test_format_jobs_context_line_shape_and_cap():
    jobs = [
        {
            "company": f"Co{i}",
            "title": f"Role {i}",
            "location": "Remote",
            "url": f"https://example.com/{i}",
        }
        for i in range(20)
    ]
    lines = format_jobs_context(jobs).splitlines()
    assert len(lines) == 15
    assert lines[0] == "Co0 — Role 0 (Remote) — https://example.com/0"
    assert lines[-1] == "Co14 — Role 14 (Remote) — https://example.com/14"


def test_format_jobs_context_omits_blank_location_and_url():
    text = format_jobs_context(
        [{"company": "Acme", "title": "Ops Lead", "location": "  ", "url": ""}]
    )
    assert text == "Acme — Ops Lead"

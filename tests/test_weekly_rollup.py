from datetime import date, timedelta

import weekly_rollup
from weekly_rollup import collect_week_digests, _format_jobs_text


class _FixedDate(date):
    _fixed = None

    @classmethod
    def today(cls):
        return cls._fixed


def _freeze(monkeypatch, d):
    fixed = _FixedDate(d.year, d.month, d.day)
    _FixedDate._fixed = fixed
    monkeypatch.setattr(weekly_rollup, "date", _FixedDate)


def test_is_friday_true_on_friday(monkeypatch):
    friday = date(2026, 8, 14)
    assert friday.weekday() == 4
    _freeze(monkeypatch, friday)
    assert weekly_rollup.is_friday() is True


def test_is_friday_false_on_thursday(monkeypatch):
    thursday = date(2026, 8, 13)
    assert thursday.weekday() == 3
    _freeze(monkeypatch, thursday)
    assert weekly_rollup.is_friday() is False


def test_collect_week_digests_finds_matching_days(tmp_path, monkeypatch):
    friday = date(2026, 8, 14)
    _freeze(monkeypatch, friday)

    monday = friday - timedelta(days=4)
    (tmp_path / f"digest_{monday.strftime('%Y%m%d')}_0900.md").write_text(
        "Monday content", encoding="utf-8"
    )
    (tmp_path / f"digest_{friday.strftime('%Y%m%d')}_1000.md").write_text(
        "Friday content", encoding="utf-8"
    )

    found = collect_week_digests(output_dir=str(tmp_path))
    labels = [label for label, _ in found]
    assert any("Monday" in l for l in labels)
    assert any("Friday" in l for l in labels)
    assert len(found) == 2


def test_collect_week_digests_uses_latest_run_of_the_day(tmp_path, monkeypatch):
    monday = date(2026, 8, 10)
    _freeze(monkeypatch, monday)

    (tmp_path / f"digest_{monday.strftime('%Y%m%d')}_0900.md").write_text(
        "earlier", encoding="utf-8"
    )
    (tmp_path / f"digest_{monday.strftime('%Y%m%d')}_1700.md").write_text(
        "later", encoding="utf-8"
    )

    found = collect_week_digests(output_dir=str(tmp_path))
    assert found[0][1] == "later"


def test_collect_week_digests_empty_when_nothing_found(tmp_path, monkeypatch):
    _freeze(monkeypatch, date(2026, 8, 14))
    assert collect_week_digests(output_dir=str(tmp_path)) == []


def test_format_jobs_text_empty():
    assert _format_jobs_text([]) == "(none)"


def test_format_jobs_text_formats_entries():
    jobs = [{"company": "Acme AI", "title": "Inference Engineer",
              "location": "Remote", "url": "https://acme/jobs/1"}]
    text = _format_jobs_text(jobs)
    assert "Acme AI" in text
    assert "Inference Engineer" in text
    assert "Remote" in text
    assert "https://acme/jobs/1" in text

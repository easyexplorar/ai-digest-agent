from datetime import datetime

from run_guard import mark_sent, sent_marker, skip_reason

MONDAY_1005 = datetime(2026, 10, 19, 10, 5)


def test_proceeds_on_weekday_after_run_time(tmp_path):
    assert skip_reason(MONDAY_1005, str(tmp_path)) is None


def test_proceeds_exactly_at_run_time(tmp_path):
    assert skip_reason(datetime(2026, 10, 19, 10, 0), str(tmp_path)) is None


def test_skips_before_run_time(tmp_path):
    assert skip_reason(datetime(2026, 10, 19, 9, 59), str(tmp_path)) == "before 10:00"


def test_skips_on_weekend(tmp_path):
    saturday = datetime(2026, 10, 17, 11, 0)
    assert skip_reason(saturday, str(tmp_path)) == "weekend"


def test_skips_once_today_is_marked_sent(tmp_path):
    mark_sent(MONDAY_1005, str(tmp_path))
    assert skip_reason(datetime(2026, 10, 19, 14, 0), str(tmp_path)) == "today's digest already sent"


def test_yesterdays_marker_does_not_block_today(tmp_path):
    mark_sent(datetime(2026, 10, 16, 10, 5), str(tmp_path))
    assert skip_reason(MONDAY_1005, str(tmp_path)) is None


def test_mark_sent_creates_output_dir(tmp_path):
    out = tmp_path / "missing"
    path = mark_sent(MONDAY_1005, str(out))
    assert path == sent_marker(MONDAY_1005, str(out))
    assert path.exists()

import os
import time

from retention import prune_output


def _touch(path, age_days):
    path.write_text("x", encoding="utf-8")
    old_time = time.time() - age_days * 86400
    os.utime(path, (old_time, old_time))


def test_deletes_files_older_than_retention_window(tmp_path):
    old_digest = tmp_path / "digest_20260101_0900.md"
    old_snapshot = tmp_path / "snapshot_20260101.json"
    _touch(old_digest, age_days=40)
    _touch(old_snapshot, age_days=40)

    deleted = prune_output(output_dir=str(tmp_path), retention_days=30)

    assert set(deleted) == {old_digest, old_snapshot}
    assert not old_digest.exists()
    assert not old_snapshot.exists()


def test_keeps_files_within_retention_window(tmp_path):
    recent = tmp_path / "digest_20260813_0900.md"
    _touch(recent, age_days=5)

    deleted = prune_output(output_dir=str(tmp_path), retention_days=30)

    assert deleted == []
    assert recent.exists()


def test_ignores_files_not_matching_tracked_patterns(tmp_path):
    stray_pdf = tmp_path / "logo_test.pdf"
    _touch(stray_pdf, age_days=90)

    deleted = prune_output(output_dir=str(tmp_path), retention_days=30)

    assert deleted == []
    assert stray_pdf.exists()


def test_second_run_is_a_noop(tmp_path):
    old_file = tmp_path / "weekly_20260101.md"
    _touch(old_file, age_days=40)

    first = prune_output(output_dir=str(tmp_path), retention_days=30)
    second = prune_output(output_dir=str(tmp_path), retention_days=30)

    assert len(first) == 1
    assert second == []


def test_missing_output_dir_returns_empty(tmp_path):
    missing = tmp_path / "does_not_exist"
    assert prune_output(output_dir=str(missing)) == []


def test_retention_days_env_var_default(tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUT_RETENTION_DAYS", "10")
    old_file = tmp_path / "digest_20260101_0900.md"
    _touch(old_file, age_days=15)

    deleted = prune_output(output_dir=str(tmp_path))  # no explicit retention_days

    assert deleted == [old_file]

import re

from notify import save_digest


def test_save_digest_writes_timestamped_markdown_file(tmp_path):
    path = save_digest("# Hello digest", output_dir=str(tmp_path))

    assert path.exists()
    assert path.suffix == ".md"
    assert re.match(r"digest_\d{8}_\d{4}\.md$", path.name)
    assert path.read_text(encoding="utf-8") == "# Hello digest"


def test_save_digest_creates_output_dir_if_missing(tmp_path):
    target = tmp_path / "nested_output"
    path = save_digest("content", output_dir=str(target))
    assert target.exists()
    assert path.parent == target

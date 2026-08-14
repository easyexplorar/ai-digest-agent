from ranker import _extract_json


def test_parses_plain_json_array():
    raw = '[{"index": 0, "novelty": 8}]'
    assert _extract_json(raw) == [{"index": 0, "novelty": 8}]


def test_strips_markdown_fences():
    raw = '```json\n[{"index": 0, "novelty": 8}]\n```'
    assert _extract_json(raw) == [{"index": 0, "novelty": 8}]


def test_strips_bare_fences_without_language_tag():
    raw = '```\n[{"index": 1}]\n```'
    assert _extract_json(raw) == [{"index": 1}]


def test_removes_trailing_commas():
    raw = '[{"index": 0, "novelty": 8,},]'
    assert _extract_json(raw) == [{"index": 0, "novelty": 8}]


def test_extracts_array_from_surrounding_commentary():
    raw = 'Here is the ranking:\n[{"index": 0}]\nHope that helps!'
    assert _extract_json(raw) == [{"index": 0}]

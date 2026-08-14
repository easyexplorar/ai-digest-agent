from dedup_utils import normalize_title


def test_lowercases_and_strips_punctuation():
    assert normalize_title("UnifoLM-VLA-Base!") == "unifolm vla base"


def test_collapses_whitespace():
    assert normalize_title("Model  release:   Foo   Bar") == "model release foo bar"


def test_distinguishes_similar_variants():
    # This is the exact false-positive case the fuzzy-match approach failed on
    # (see dedup_utils.py docstring) — these must NOT normalize to the same key.
    a = normalize_title("Model release: org/UnifoLM-VLA-Base")
    b = normalize_title("Model release: org/UnifoLM-VLA-Libero")
    assert a != b


def test_identical_titles_normalize_equal():
    a = normalize_title("GPT-5: A New Era!")
    b = normalize_title("gpt 5 a new era")
    assert a == b

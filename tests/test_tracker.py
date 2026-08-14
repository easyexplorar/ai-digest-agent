import json
from datetime import date, timedelta

from tracker import (
    save_snapshot, load_snapshot, load_yesterday,
    save_seen_urls, load_seen_urls,
    discipline_tally, trend_delta,
    format_tally_text, format_delta_text, format_china_context,
)


def _items(n):
    return [
        {"title": f"Item {i}", "source": "arXiv", "url": f"https://x/{i}",
         "score": 10 - i, "discipline": "Model Release", "reason": "r"}
        for i in range(n)
    ]


def test_save_and_load_snapshot_roundtrip(tmp_path):
    items = _items(3)
    path = save_snapshot(items, output_dir=str(tmp_path))
    assert path.exists()

    loaded = load_snapshot(date.today(), output_dir=str(tmp_path))
    assert [i["title"] for i in loaded] == [i["title"] for i in items]


def test_save_snapshot_caps_at_top_30(tmp_path):
    save_snapshot(_items(45), output_dir=str(tmp_path))
    loaded = load_snapshot(date.today(), output_dir=str(tmp_path))
    assert len(loaded) == 30


def test_load_snapshot_missing_date_returns_empty(tmp_path):
    assert load_snapshot(date.today(), output_dir=str(tmp_path)) == []


def test_load_yesterday_steps_back_up_to_four_days(tmp_path):
    three_days_ago = date.today() - timedelta(days=3)
    filename = tmp_path / f"snapshot_{three_days_ago.strftime('%Y%m%d')}.json"
    filename.write_text(json.dumps([{"title": "Weekend item"}]), encoding="utf-8")

    result = load_yesterday(output_dir=str(tmp_path))
    assert result == [{"title": "Weekend item"}]


def test_load_yesterday_returns_empty_when_nothing_found(tmp_path):
    assert load_yesterday(output_dir=str(tmp_path)) == []


def test_save_seen_urls_writes_sorted_deduped_urls(tmp_path):
    items = [{"url": "https://b"}, {"url": "https://a"}, {"url": "https://a"}, {"url": None}]
    path = save_seen_urls(items, output_dir=str(tmp_path))
    assert json.loads(path.read_text(encoding="utf-8")) == ["https://a", "https://b"]


def test_load_seen_urls_excludes_todays_own_file(tmp_path):
    # load_seen_urls looks back starting at "yesterday" so today's run never
    # filters itself out against the urls it just saved (see tracker.py).
    items = [{"url": "https://a"}, {"url": "https://b"}, {"url": None}]
    save_seen_urls(items, output_dir=str(tmp_path))

    seen = load_seen_urls(output_dir=str(tmp_path), days=3)
    assert seen == set()


def test_load_seen_urls_picks_up_prior_days_file(tmp_path):
    yesterday = date.today() - timedelta(days=1)
    urls_path = tmp_path / f"urls_{yesterday.strftime('%Y%m%d')}.json"
    urls_path.write_text(json.dumps(["https://a", "https://b"]), encoding="utf-8")

    seen = load_seen_urls(output_dir=str(tmp_path), days=3)
    assert seen == {"https://a", "https://b"}


def test_load_seen_urls_falls_back_to_snapshot_when_no_urls_log(tmp_path):
    yesterday = date.today() - timedelta(days=1)
    snap_path = tmp_path / f"snapshot_{yesterday.strftime('%Y%m%d')}.json"
    snap_path.write_text(json.dumps([{"url": "https://legacy"}]), encoding="utf-8")

    seen = load_seen_urls(output_dir=str(tmp_path), days=3)
    assert "https://legacy" in seen


def test_discipline_tally_counts_top_n():
    items = (
        [{"discipline": "Model Release"}] * 3
        + [{"discipline": "Agent Frameworks & Orchestration"}] * 2
        + [{"discipline": "Other"}] * 20  # beyond top_n=15, should be excluded
    )
    tally = discipline_tally(items, top_n=5)
    assert sum(tally.values()) == 5


def test_trend_delta_splits_new_and_recurring():
    yesterday = [{"title": "Recurring Item"}]
    today = [{"title": "Recurring Item"}, {"title": "Brand New Item"}]

    delta = trend_delta(today, yesterday)
    assert [i["title"] for i in delta["new"]] == ["Brand New Item"]
    assert [i["title"] for i in delta["recurring"]] == ["Recurring Item"]


def test_format_tally_text_empty():
    assert format_tally_text({}) == "No discipline data available."


def test_format_delta_text_no_prior_data():
    delta = {"new": [], "recurring": []}
    text = format_delta_text(delta)
    assert "(no prior data)" in text
    assert "(none)" in text


def test_format_china_context_filters_by_discipline_not_overall_rank():
    # Regression test for the bug this fixed: China items ranked outside the
    # overall top 10 were invisible to the digest's China AI Watch section
    # because generate_digest only saw ranked_items[:10]. This must pull
    # from the full ranked list regardless of score/position.
    ranked = [
        {"title": "Top agent paper", "source": "arXiv", "url": "https://x/1",
         "score": 29, "discipline": "Agent Security", "reason": "r"},
        {"title": "DeepSeek release", "source": "DeepSeek (HuggingFace)", "url": "https://x/2",
         "score": 12, "discipline": "Chinese Lab Developments", "reason": "new model"},
        {"title": "Unitree demo", "source": "Unitree Robotics (Robotics HF)", "url": "https://x/3",
         "score": 10, "discipline": "Chinese Embodied AI & Robotics", "reason": "new robot"},
    ]
    text = format_china_context(ranked)
    assert "DeepSeek release" in text
    assert "Unitree demo" in text
    assert "Top agent paper" not in text


def test_format_china_context_empty_when_no_china_items():
    ranked = [{"title": "Other", "source": "arXiv", "url": "https://x",
               "score": 20, "discipline": "Model Release", "reason": ""}]
    assert format_china_context(ranked) == "No Chinese lab or robotics items detected today."


def test_format_china_context_caps_at_top_n():
    ranked = [
        {"title": f"Item {i}", "source": "DeepSeek (HuggingFace)", "url": f"https://x/{i}",
         "score": 10, "discipline": "Chinese Lab Developments", "reason": ""}
        for i in range(8)
    ]
    text = format_china_context(ranked, top_n=3)
    assert text.count("Item") == 3

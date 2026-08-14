from frontier_voices import tag_frontier_voices


def test_tags_by_known_source():
    items = [{"source": "Thinking Machines Lab Blog", "title": "New post", "summary": ""}]
    tag_frontier_voices(items)
    assert items[0]["frontier_voice"] == "Thinking Machines Lab (Mira Murati)"


def test_tags_by_title_keyword():
    items = [{"source": "Hacker News", "title": "Ilya Sutskever announces new results", "summary": ""}]
    tag_frontier_voices(items)
    assert items[0]["frontier_voice"] == "Safe Superintelligence (Ilya Sutskever)"


def test_tags_by_summary_keyword():
    items = [{"source": "Hacker News", "title": "A new model", "summary": "Built by researchers at AMI Labs."}]
    tag_frontier_voices(items)
    assert items[0]["frontier_voice"] == "AMI Labs (Yann LeCun)"


def test_keyword_match_is_case_insensitive():
    items = [{"source": "Hacker News", "title": "JEFF DEAN launches new venture", "summary": ""}]
    tag_frontier_voices(items)
    assert items[0]["frontier_voice"] == "Discovery Loop (Jeff Dean)"


def test_untagged_items_get_no_frontier_voice_key():
    items = [{"source": "arXiv", "title": "Unrelated paper", "summary": "Nothing to do with any tracked lab."}]
    tag_frontier_voices(items)
    assert "frontier_voice" not in items[0]


def test_returns_same_list_mutated_in_place():
    items = [{"source": "Thinking Machines Lab Blog", "title": "x", "summary": ""}]
    result = tag_frontier_voices(items)
    assert result is items

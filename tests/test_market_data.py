from sources.market_data import _pct_in_52w_range, format_market_context


def test_pct_in_52w_range_midpoint():
    assert _pct_in_52w_range(price=150, low=100, high=200) == "50% of 52w range"


def test_pct_in_52w_range_at_high():
    assert _pct_in_52w_range(price=200, low=100, high=200) == "100% of 52w range"


def test_pct_in_52w_range_zero_range_is_na():
    assert _pct_in_52w_range(price=100, low=100, high=100) == "N/A"


def test_pct_in_52w_range_no_price_is_na():
    assert _pct_in_52w_range(price=0, low=100, high=200) == "N/A"


def test_format_market_context_empty():
    assert format_market_context({}) == "Market data unavailable."


def test_format_market_context_formats_gain():
    data = {
        "NVDA": {
            "price": 120.5, "pct_change": 2.34,
            "w52_low": 80.0, "w52_high": 150.0, "range_pos": "58% of 52w range",
            "earnings": "N/A", "analyst_rec": "N/A", "num_analysts": 0,
        }
    }
    line = format_market_context(data)
    assert "NVDA" in line
    assert "$120.50" in line
    assert "+2.3%" in line
    assert "Earnings" not in line  # N/A earnings should be omitted
    assert "Analyst" not in line  # N/A rec should be omitted


def test_format_market_context_formats_loss_without_plus_sign():
    data = {
        "META": {
            "price": 300.0, "pct_change": -1.5,
            "w52_low": 0.0, "w52_high": 0.0, "range_pos": "N/A",
            "earnings": "N/A", "analyst_rec": "N/A", "num_analysts": 0,
        }
    }
    line = format_market_context(data)
    assert "-1.5%" in line
    assert "+-1.5%" not in line

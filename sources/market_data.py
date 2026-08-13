"""Live market context for US AI-exposed tickers via yfinance."""

from datetime import datetime, timezone

import yfinance as yf

# The ~15 tickers referenced in the digest prompt's Market Signals section
TICKERS = [
    "NVDA", "MSFT", "GOOGL", "META", "AMZN",
    "AMD", "AVGO", "ARM", "INTC", "SMCI",
    "PLTR", "TSLA", "ORCL",
]


def _pct_in_52w_range(price: float, low: float, high: float) -> str:
    if high > low and price:
        pct = (price - low) / (high - low) * 100
        return f"{pct:.0f}% of 52w range"
    return "N/A"


def _next_earnings(t: yf.Ticker) -> str:
    """Return the next upcoming earnings date from ticker.calendar."""
    try:
        dates = (t.calendar or {}).get("Earnings Date", [])
        today = datetime.now(timezone.utc).date()
        future = [d for d in dates if d >= today]
        if not future:
            return "N/A"
        nxt = min(future)
        days = (nxt - today).days
        return f"{nxt.strftime('%d %b %Y')} (in {days}d)"
    except Exception:
        return "N/A"


def fetch_market_data(tickers: list[str] = TICKERS) -> dict[str, dict]:
    """Return a dict keyed by ticker symbol with price/range/earnings/analyst data."""
    results: dict[str, dict] = {}
    for symbol in tickers:
        try:
            t    = yf.Ticker(symbol)
            info = t.info
            price = info.get("currentPrice") or info.get("regularMarketPrice") or 0.0
            prev  = info.get("previousClose") or info.get("regularMarketPreviousClose") or 0.0
            pct   = ((price - prev) / prev * 100) if prev else 0.0

            w52_low  = info.get("fiftyTwoWeekLow",  0.0)
            w52_high = info.get("fiftyTwoWeekHigh", 0.0)

            rec          = (info.get("recommendationKey") or "N/A").replace("_", " ").title()
            num_analysts = info.get("numberOfAnalystOpinions") or 0

            results[symbol] = {
                "price":        price,
                "pct_change":   pct,
                "w52_low":      w52_low,
                "w52_high":     w52_high,
                "range_pos":    _pct_in_52w_range(price, w52_low, w52_high),
                "earnings":     _next_earnings(t),
                "analyst_rec":  rec,
                "num_analysts": num_analysts,
            }
        except Exception as e:
            print(f"    [warning] market data for {symbol} failed: {e}")
    return results


def format_market_context(data: dict[str, dict]) -> str:
    """Format market data into a compact text block for the digest prompt."""
    if not data:
        return "Market data unavailable."
    lines = []
    for symbol, d in data.items():
        sign  = "+" if d["pct_change"] >= 0 else ""
        price = f"${d['price']:.2f}" if d["price"] else "N/A"
        chg   = f"{sign}{d['pct_change']:.1f}%" if d["price"] else ""
        w52   = (f"52w ${d['w52_low']:.0f}-${d['w52_high']:.0f} ({d['range_pos']})"
                 if d["w52_low"] else "")
        earn  = f"Earnings: {d['earnings']}" if d["earnings"] != "N/A" else ""
        ana   = (f"Analyst: {d['analyst_rec']} ({d['num_analysts']} analysts)"
                 if d["analyst_rec"] != "N/A" else "")
        parts = [p for p in [price, chg, w52, earn, ana] if p]
        lines.append(f"  {symbol}: {' | '.join(parts)}")
    return "\n".join(lines)

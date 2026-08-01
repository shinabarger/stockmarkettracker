"""
Fetch VTSAX daily closing prices and update the local history file.

This script is designed to run on a schedule (see .github/workflows/update-data.yml).
It is idempotent: running it multiple times on the same day, or on a day the
market was closed, will not corrupt or duplicate the stored history.

Behavior:
    - If data/vtsax_history.json is missing or empty, pull the full available
      history from Yahoo Finance (a one-time backfill).
    - Otherwise, pull just the last few trading days and merge in anything new.
    - The merged history is de-duplicated by date, sorted chronologically,
      and written back out with stable formatting.
"""

import json
from pathlib import Path

import yfinance as yf

TICKER = "VTSAX"
DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "vtsax_history.json"

# When we already have history on disk, we only need to look back a short
# window to pick up the latest close (and to backfill anything a previous
# run may have missed, e.g. after an outage).
RECENT_WINDOW = "10d"
FULL_BACKFILL = "max"


def load_existing_history() -> dict[str, float]:
    """Return {date_str: close_price} from the existing data file, or {} if none."""
    if not DATA_FILE.exists():
        return {}

    raw_text = DATA_FILE.read_text().strip()
    if not raw_text:
        return {}

    records = json.loads(raw_text)
    return {record["date"]: record["close"] for record in records}


def fetch_prices(period: str) -> dict[str, float]:
    """Fetch daily closing prices for TICKER over the given yfinance period."""
    history = yf.Ticker(TICKER).history(period=period, interval="1d")

    prices: dict[str, float] = {}
    for timestamp, row in history.iterrows():
        date_str = timestamp.strftime("%Y-%m-%d")
        prices[date_str] = round(float(row["Close"]), 4)
    return prices


def save_history(prices_by_date: dict[str, float]) -> None:
    """Write the merged history to disk as a sorted, pretty-printed JSON array."""
    records = [
        {"date": date_str, "close": close}
        for date_str, close in sorted(prices_by_date.items())
    ]

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(records, indent=2) + "\n")


def main() -> None:
    existing = load_existing_history()

    period = FULL_BACKFILL if not existing else RECENT_WINDOW
    fetched = fetch_prices(period)

    merged = {**existing, **fetched}

    added = sorted(set(merged) - set(existing))
    save_history(merged)

    if added:
        print(f"Added {len(added)} new trading day(s): {', '.join(added)}")
    else:
        print("No new trading days found (market likely closed).")


if __name__ == "__main__":
    main()

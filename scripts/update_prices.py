"""
Fetch daily closing prices for every ticker in data/universe.json and update
each ticker's history file under data/prices/<SYMBOL>.json.

Same idempotent approach the original single-ticker script used: a ticker
with no history file yet gets a full backfill, everything else just gets a
short recent window merged in. Tickers are processed in batches so one bad
symbol, or a temporary Yahoo hiccup, doesn't take down the whole run.

The very first run backfills the full universe (thousands of tickers), so
it will take a lot longer than every run after that. See
.github/workflows/update-data.yml for the timeout this needs.
"""

import json
import time
from pathlib import Path

import yfinance as yf

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
UNIVERSE_FILE = DATA_DIR / "universe.json"
PRICES_DIR = DATA_DIR / "prices"

# The very first version of this project stored VTSAX's history at this
# path. If it's still there, seed the new per-ticker file from it so that
# history isn't lost in the move to data/prices/.
LEGACY_VTSAX_FILE = DATA_DIR / "vtsax_history.json"

BATCH_SIZE = 100
SECONDS_BETWEEN_BATCHES = 2
RECENT_WINDOW = "10d"
FULL_BACKFILL = "max"


def load_universe_symbols() -> list[str]:
    tickers = json.loads(UNIVERSE_FILE.read_text())
    return [ticker["symbol"] for ticker in tickers]


def history_file(symbol: str) -> Path:
    return PRICES_DIR / f"{symbol}.json"


def load_existing_history(symbol: str) -> dict[str, float]:
    """Return whatever price history is already on disk for this symbol.

    Note this deliberately doesn't count as "the file exists" for batching
    purposes (see update_batch): VTSAX still needs its one-time full
    backfill even though we're carrying its old history forward, so that it
    ends up with the same multi-year depth every other ticker gets.
    """
    path = history_file(symbol)
    if path.exists():
        raw_text = path.read_text().strip()
        return {record["date"]: record["close"] for record in json.loads(raw_text)} if raw_text else {}

    if symbol == "VTSAX" and LEGACY_VTSAX_FILE.exists():
        raw_text = LEGACY_VTSAX_FILE.read_text().strip()
        return {record["date"]: record["close"] for record in json.loads(raw_text)} if raw_text else {}

    return {}


def save_history(symbol: str, prices_by_date: dict[str, float]) -> None:
    records = [
        {"date": date_str, "close": close}
        for date_str, close in sorted(prices_by_date.items())
    ]

    path = history_file(symbol)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, indent=2) + "\n")


def batched(items: list[str], size: int):
    for start in range(0, len(items), size):
        yield items[start:start + size]


def fetch_batch_prices(symbols: list[str], period: str) -> dict[str, dict[str, float]]:
    """Return {symbol: {date: close}} for a batch of tickers."""
    data = yf.download(
        tickers=" ".join(symbols),
        period=period,
        interval="1d",
        group_by="ticker",
        auto_adjust=False,
        threads=True,
        progress=False,
    )

    is_single_symbol = len(symbols) == 1
    prices_by_symbol: dict[str, dict[str, float]] = {}

    for symbol in symbols:
        try:
            closes = (data if is_single_symbol else data[symbol])["Close"].dropna()
            prices = {
                timestamp.strftime("%Y-%m-%d"): round(float(close), 4)
                for timestamp, close in closes.items()
            }
            if prices:
                prices_by_symbol[symbol] = prices
        except (KeyError, TypeError):
            continue  # symbol had no usable data in this batch; skip it

    return prices_by_symbol


def update_ticker_file(symbol: str, fetched_prices: dict[str, float]) -> int:
    """Merge freshly fetched prices into the ticker's file. Returns how many
    new dates were added."""
    existing = load_existing_history(symbol)
    merged = {**existing, **fetched_prices}
    save_history(symbol, merged)
    return len(merged) - len(existing)


def update_batch(symbols: list[str]) -> int:
    """Fetch and save one batch of tickers, split by whether each one needs
    a full backfill or just a recent-window refresh. Returns the total
    number of new price points added."""
    new_symbols = [s for s in symbols if not history_file(s).exists()]
    existing_symbols = [s for s in symbols if s not in new_symbols]

    added = 0
    for symbols_in_group, period in [(new_symbols, FULL_BACKFILL), (existing_symbols, RECENT_WINDOW)]:
        if not symbols_in_group:
            continue
        try:
            fetched = fetch_batch_prices(symbols_in_group, period)
        except Exception as err:  # a whole batch failing shouldn't stop the run
            print(f"  fetch failed for {len(symbols_in_group)} symbols ({period}): {err}")
            continue
        for symbol in symbols_in_group:
            added += update_ticker_file(symbol, fetched.get(symbol, {}))

    return added


def main() -> None:
    symbols = load_universe_symbols()
    print(f"Updating {len(symbols)} tickers...")

    total_added = 0
    batches = list(batched(symbols, BATCH_SIZE))
    for batch_num, batch in enumerate(batches, start=1):
        added = update_batch(batch)
        total_added += added
        print(f"Batch {batch_num}/{len(batches)}: {len(batch)} tickers, {added} new price points")
        time.sleep(SECONDS_BETWEEN_BATCHES)

    print(f"Done. {total_added} new price points added across all tickers.")


if __name__ == "__main__":
    main()

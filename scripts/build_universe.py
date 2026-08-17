"""
Build the list of tickers this dashboard can track: every S&P 500
constituent, every stock listed on Nasdaq, plus a small hand-picked list of
extras that aren't exchange-listed common stock (like the VTSAX mutual fund
this project started with).

This runs on its own, slower schedule (see
.github/workflows/update-universe.yml) separate from the daily price update,
since index membership and exchange listings change far less often than
closing prices do.
"""

import json
from io import StringIO
from pathlib import Path

import pandas as pd
import requests

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
UNIVERSE_FILE = DATA_DIR / "universe.json"

SP500_WIKIPEDIA_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
NASDAQ_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"

REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; vtsax-tracker-bot/1.0)"}

# Tickers we always want available, even though they aren't part of the S&P
# 500 or listed on Nasdaq.
EXTRA_TICKERS = [
    {"symbol": "VTSAX", "name": "Vanguard Total Stock Market Index Fund"},
    {"symbol": "VTI", "name": "Vanguard Total Stock Market ETF"},
]


def fetch_sp500_constituents() -> list[dict]:
    """Return [{symbol, name}, ...] for the current S&P 500, from Wikipedia."""
    response = requests.get(SP500_WIKIPEDIA_URL, headers=REQUEST_HEADERS, timeout=30)
    response.raise_for_status()

    constituents_table = pd.read_html(StringIO(response.text))[0]

    return [
        {
            "symbol": str(row["Symbol"]).strip().replace(".", "-"),
            "name": str(row["Security"]).strip(),
        }
        for _, row in constituents_table.iterrows()
    ]


def fetch_nasdaq_listed() -> list[dict]:
    """Return [{symbol, name}, ...] for every security listed on Nasdaq."""
    response = requests.get(NASDAQ_LISTED_URL, headers=REQUEST_HEADERS, timeout=30)
    response.raise_for_status()

    # The file is pipe-delimited, with a header row and a file-timestamp
    # footer row that isn't ticker data.
    lines = response.text.strip().splitlines()
    rows = lines[1:-1]

    tickers = []
    for row in rows:
        fields = row.split("|")
        symbol, name, test_issue = fields[0].strip(), fields[1].strip(), fields[3].strip()
        if not symbol or test_issue == "Y":
            continue  # skip Nasdaq's internal test symbols
        tickers.append({"symbol": symbol, "name": name})
    return tickers


def merge_unique(*ticker_lists: list[dict]) -> list[dict]:
    """Combine ticker lists, keeping the first occurrence of each symbol."""
    merged: dict[str, dict] = {}
    for ticker_list in ticker_lists:
        for ticker in ticker_list:
            merged.setdefault(ticker["symbol"], ticker)
    return sorted(merged.values(), key=lambda t: t["symbol"])


def save_universe(tickers: list[dict]) -> None:
    UNIVERSE_FILE.parent.mkdir(parents=True, exist_ok=True)
    UNIVERSE_FILE.write_text(json.dumps(tickers, indent=2) + "\n")


def main() -> None:
    sp500 = fetch_sp500_constituents()
    nasdaq = fetch_nasdaq_listed()
    universe = merge_unique(EXTRA_TICKERS, sp500, nasdaq)

    save_universe(universe)

    print(f"S&P 500 constituents: {len(sp500)}")
    print(f"Nasdaq-listed securities: {len(nasdaq)}")
    print(f"Total unique tickers in universe: {len(universe)}")


if __name__ == "__main__":
    main()

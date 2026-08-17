# VTSAX Tracker

https://shinabarger.github.io/vtsax-tracker/ is a one-click, dashboard for VTSAX (Vanguard Total Stock Market Index
Fund, Admiral Shares). Shows the current value and how it has updated since the
start of the month, the start of the year, the past year, or however many
years back you would like to examine.

## How it works

`scripts/build_universe.py` builds the list of tickers the tool can track.
It pulls the current S&P 500 list from Wikipedia and every stock listed on
Nasdaq from Nasdaq's own public symbol directory, then writes the combined
list to `data/universe.json`. A scheduled job runs this weekly, since index
membership and exchange listings barely change day to day.

`scripts/update_prices.py` reads that list and keeps one price history file
per ticker under `data/prices/`, pulling closes from Yahoo Finance. A
scheduled job runs this daily, around 6:30pm ET on weekdays, with a backup
run around 9:30pm ET in case a price posts late.

`index.html` reads `data/universe.json` for the search box and whichever
ticker's price file is selected for everything else, entirely in the
browser. It is static, so hosting is free and the page stays live with
nothing to maintain.

A ticker with no history file yet gets a full backfill the first time it
runs. Every run after that just checks the last ten days and adds anything
new. The first daily run has to backfill the entire universe, thousands of
tickers, so it will take a long time. Every run after that is quick.

## Setup

1. Under Settings, then Actions, then General, set Workflow permissions to
   Read and write. The scheduled jobs need this to commit updated data back
   to the repo.
2. Under Settings, then Pages, set Source to the main branch, folder root.
3. Open the Actions tab and run "Update ticker universe" once to build the
   ticker list.
4. Once that finishes, run "Update stock prices" once to do the first
   backfill. This one takes a while. That is expected.
5. Once Pages finishes deploying, the dashboard is live.

## Notes

- Tracking thousands of Nasdaq tickers means the daily job does a lot more
  work than it did when this only tracked VTSAX. It is still free, but
  Yahoo Finance is an unofficial data source, not a paid API with
  guaranteed limits, so there is a small chance it throttles requests at
  that volume.
- The daily job only runs on weekdays. On a market holiday that falls on a
  weekday, it still runs, finds no new price, and skips the commit.
- The data folder will grow as more tickers build up history. If it gets
  too large, trim how far back the price fetch backfills instead of
  pulling full history for every new ticker.
- This is for my own tracking. None of it is financial advice.

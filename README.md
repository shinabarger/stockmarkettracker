# VTSAX Tracker

https://shinabarger.github.io/vtsax-tracker/ is a one-click, dashboard for VTSAX (Vanguard Total Stock Market Index
Fund, Admiral Shares). Shows the current value and how it has updated since the
start of the month, the start of the year, the past year, or however many
years back you would like to examine.

## How it works

There's no backend server. Two pieces do all the work:

1. **`scripts/update_vtsax_data.py`** pulls the latest VTSAX close from Yahoo
   Finance (via the `yfinance` library) and appends it to
   `data/vtsax_history.json`.
2. **`.github/workflows/update-data.yml`** runs that script automatically on
   a schedule (~6:30pm ET on weekdays, with a ~9:30pm ET backup run in case a
   NAV posts late) and commits the updated data file back to the repo.

`index.html` is a static page that reads `data/vtsax_history.json` and
renders the chart and toggle buttons entirely in the browser. Because it's
just static files, GitHub Pages can serve it for free, and it's live 24/7 with
no server to maintain.

The first time the workflow runs, it'll notice there's no history yet and
pull the full available price history in one shot (this may take a little
longer than later runs, which only check the last 10 days).


## Notes

- This is a public repo pattern (scheduled Action + static Pages site), so it
  runs on GitHub's free tier with no cost.
- The schedule only triggers on weekdays. On market holidays that fall on a
  weekday, the workflow still runs but finds no new close and skips the
  commit, so nothing breaks.
- If you ever want to change the fund tracked, update `TICKER` in
  `scripts/update_vtsax_data.py`.
- This dashboard is for personal tracking only. Nothing here is financial
  advice.

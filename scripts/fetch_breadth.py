from pathlib import Path
from io import StringIO

import pandas as pd
import requests
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
RAW.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)

# GitHub-hosted open dataset, sourced from Wikipedia and updated regularly.
# Using raw.githubusercontent.com avoids Wikipedia HTTP 403 errors on GitHub Actions runners.
CONSTITUENTS_URL = (
    "https://raw.githubusercontent.com/"
    "datasets/s-and-p-500-companies/refs/heads/main/data/constituents.csv"
)

cache_file = RAW / "sp500_constituents.csv"

def load_constituents():
    try:
        response = requests.get(
            CONSTITUENTS_URL,
            timeout=30,
            headers={"User-Agent": "market-leadership-dashboard/1.0"},
        )
        response.raise_for_status()
        const = pd.read_csv(StringIO(response.text))
        needed = ["Symbol", "Security", "GICS Sector", "GICS Sub-Industry"]
        missing = [c for c in needed if c not in const.columns]
        if missing:
            raise ValueError(f"Constituent dataset missing columns: {missing}")
        const = const[needed].copy()
        const["yf_symbol"] = (
            const["Symbol"].astype(str).str.replace(".", "-", regex=False)
        )
        const.to_csv(cache_file, index=False)
        return const
    except Exception as exc:
        # On later weekly runs, use the last successful constituent list if the
        # remote source is temporarily unavailable.
        if cache_file.exists():
            print(f"WARNING: constituent refresh failed ({exc}); using cached list.")
            const = pd.read_csv(cache_file)
            if "yf_symbol" not in const.columns:
                const["yf_symbol"] = (
                    const["Symbol"].astype(str).str.replace(".", "-", regex=False)
                )
            return const
        raise RuntimeError(
            f"Unable to load S&P 500 constituents and no cache exists: {exc}"
        ) from exc

const = load_constituents()
tickers = const["yf_symbol"].dropna().drop_duplicates().tolist()
all_close = []

# Batch downloads reduce Yahoo Finance throttling risk.
for i in range(0, len(tickers), 80):
    batch = tickers[i:i + 80]
    d = yf.download(
        batch,
        period="2y",
        interval="1d",
        auto_adjust=True,
        actions=False,
        progress=False,
        threads=True,
        group_by="column",
    )
    if d.empty:
        continue

    if isinstance(d.columns, pd.MultiIndex):
        if "Close" not in d.columns.get_level_values(0):
            continue
        c = d["Close"].copy()
    else:
        c = d[["Close"]].copy()
        c.columns = [batch[0]]

    all_close.append(c)

if not all_close:
    raise RuntimeError("No S&P 500 constituent prices returned.")

close = pd.concat(all_close, axis=1)
close = close.loc[:, ~close.columns.duplicated()].sort_index()
close.index = pd.to_datetime(close.index).tz_localize(None)
close.to_csv(RAW / "sp500_close_wide.csv", index_label="date")

spy = yf.download(
    "SPY",
    period="2y",
    interval="1d",
    auto_adjust=True,
    actions=False,
    progress=False,
)

if spy.empty:
    raise RuntimeError("No SPY data returned.")

spy_close = spy["Close"]
if isinstance(spy_close, pd.DataFrame):
    spy_close = spy_close.iloc[:, 0]

spy_close.index = pd.to_datetime(spy_close.index).tz_localize(None)

windows = [21, 63, 126, 252]
rows = []
dates = close.index[-140:]  # dashboard history ~= 6 months

for dt in dates:
    pos = close.index.get_indexer([dt])[0]

    for n in windows:
        if pos < n:
            continue

        start_dt = close.index[pos - n]
        stock_r = close.loc[dt] / close.loc[start_dt] - 1

        spy_slice = spy_close.loc[:dt]
        if len(spy_slice) <= n:
            continue

        spy_r = spy_slice.iloc[-1] / spy_slice.iloc[-(n + 1)] - 1
        valid = stock_r.dropna()

        # Avoid publishing a misleading breadth reading when too many
        # constituent price series failed to download.
        if len(valid) < 300:
            continue

        breadth = (valid > spy_r).mean()

        rows.append(
            {
                "date": dt.date().isoformat(),
                "window": n,
                "breadth_pct": float(breadth),
                "n_valid": int(len(valid)),
                "definition": (
                    "Percent of current S&P 500 constituents outperforming "
                    "SPY over trailing window"
                ),
            }
        )

hist = pd.DataFrame(rows)

if hist.empty:
    raise RuntimeError(
        "Breadth calculation produced no valid observations. "
        "Check Yahoo Finance downloads."
    )

hist.to_csv(OUT / "breadth_history.csv", index=False)

latest = (
    hist.sort_values("date")
    .groupby("window", as_index=False)
    .tail(1)
    .rename(columns={"date": "as_of"})
)
latest.to_csv(OUT / "breadth_latest.csv", index=False)

print(
    f"Breadth files updated using {len(tickers)} constituents; "
    f"latest date={hist['date'].max()}."
)

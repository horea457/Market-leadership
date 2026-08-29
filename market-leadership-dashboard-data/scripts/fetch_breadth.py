from pathlib import Path
import math
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
RAW.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)

tables = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
const = tables[0][["Symbol","Security","GICS Sector","GICS Sub-Industry"]].copy()
const["yf_symbol"] = const["Symbol"].str.replace(".", "-", regex=False)
const.to_csv(RAW / "sp500_constituents.csv", index=False)

tickers = const["yf_symbol"].tolist()
all_close = []

# Batch to reduce rate-limit risk.
for i in range(0, len(tickers), 80):
    batch = tickers[i:i+80]
    d = yf.download(
        batch, period="2y", interval="1d", auto_adjust=True,
        actions=False, progress=False, threads=True, group_by="column"
    )
    if d.empty:
        continue
    if isinstance(d.columns, pd.MultiIndex):
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

spy = yf.download("SPY", period="2y", interval="1d", auto_adjust=True, progress=False)
if spy.empty:
    raise RuntimeError("No SPY data returned.")
spy_close = spy["Close"]
if isinstance(spy_close, pd.DataFrame):
    spy_close = spy_close.iloc[:,0]
spy_close.index = pd.to_datetime(spy_close.index).tz_localize(None)

windows = [21,63,126,252]
rows = []
dates = close.index[-140:]  # dashboard history ~= 6 months
for dt in dates:
    for n in windows:
        pos = close.index.get_indexer([dt])[0]
        if pos < n:
            continue
        start_dt = close.index[pos-n]
        stock_r = close.loc[dt] / close.loc[start_dt] - 1
        spy_slice = spy_close.loc[:dt]
        if len(spy_slice) <= n:
            continue
        spy_r = spy_slice.iloc[-1] / spy_slice.iloc[-(n+1)] - 1
        valid = stock_r.dropna()
        if len(valid) < 300:
            continue
        breadth = (valid > spy_r).mean()
        rows.append({
            "date": dt.date().isoformat(),
            "window": n,
            "breadth_pct": float(breadth),
            "n_valid": int(len(valid)),
            "definition": "Percent of S&P 500 constituents outperforming SPY over trailing window"
        })

hist = pd.DataFrame(rows)
hist.to_csv(OUT / "breadth_history.csv", index=False)
if not hist.empty:
    latest = hist.sort_values("date").groupby("window", as_index=False).tail(1)
    latest = latest.rename(columns={"date":"as_of"})
    latest.to_csv(OUT / "breadth_latest.csv", index=False)

print("Breadth files updated.")

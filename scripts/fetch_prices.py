from pathlib import Path
import os
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "config"
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

inst = pd.read_csv(CFG / "instruments.csv")
tickers = inst["ticker"].dropna().astype(str).tolist()

baskets = CFG / "baskets.csv"
if baskets.exists():
    b = pd.read_csv(baskets)
    if "ticker" in b.columns:
        tickers += b["ticker"].dropna().astype(str).tolist()

tickers = list(dict.fromkeys(tickers))
period = os.getenv("PRICE_HISTORY_PERIOD", "10y")

parts = []
for i in range(0, len(tickers), 80):
    batch = tickers[i:i+80]
    d = yf.download(
        batch,
        period=period,
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
    parts.append(c)

if not parts:
    raise RuntimeError("No price data downloaded.")

close = pd.concat(parts, axis=1)
close = close.loc[:, ~close.columns.duplicated()].sort_index()
close.index = pd.to_datetime(close.index).tz_localize(None)
close.to_csv(RAW / "prices_close_wide.csv", index_label="date")

missing = [t for t in tickers if t not in close.columns or close[t].dropna().empty]
print(f"Price history updated: {len(close)} rows, {len(close.columns)} tickers, period={period}")
if missing:
    print("WARNING missing tickers:", ", ".join(missing))

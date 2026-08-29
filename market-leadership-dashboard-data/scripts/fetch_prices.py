from pathlib import Path
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "instruments.csv"
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

cfg = pd.read_csv(CONFIG)
tickers = cfg["ticker"].drop_duplicates().tolist()

data = yf.download(
    tickers=tickers,
    period="5y",
    interval="1d",
    auto_adjust=True,
    actions=False,
    progress=False,
    group_by="column",
    threads=True,
)

if data.empty:
    raise RuntimeError("No price data returned by yfinance.")

if isinstance(data.columns, pd.MultiIndex):
    # yfinance multi-ticker format: first level field, second level ticker.
    close = data["Close"].copy()
else:
    close = data[["Close"]].copy()
    close.columns = [tickers[0]]

close.index = pd.to_datetime(close.index).tz_localize(None)
close = close.sort_index().dropna(how="all")
close.to_csv(RAW / "prices_close_wide.csv", index_label="date")

long = close.stack(dropna=True).rename("adj_close").reset_index()
long.columns = ["date", "ticker", "adj_close"]
long.to_csv(RAW / "prices_close_long.csv", index=False)

print(f"Saved {len(close):,} trading days for {len(close.columns)} tickers.")

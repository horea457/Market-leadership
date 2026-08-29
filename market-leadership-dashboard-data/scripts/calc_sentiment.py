from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
MANUAL = ROOT / "data" / "manual"
OUT.mkdir(parents=True, exist_ok=True)

fred = pd.read_csv(RAW / "fred_sentiment_proxies.csv", parse_dates=["date"], index_col="date").sort_index()
prices = pd.read_csv(RAW / "prices_close_wide.csv", parse_dates=["date"], index_col="date").sort_index()
spy = prices["SPY"].dropna()

def percentile_rank(series, value, years=5):
    s = series.dropna()
    if len(s) == 0 or pd.isna(value):
        return np.nan
    cutoff = s.index.max() - pd.DateOffset(years=years)
    s = s[s.index >= cutoff]
    return float((s <= value).mean() * 100)

vix = fred["vix"].dropna()
hy = fred["hy_oas"].dropna()
vix_now = vix.iloc[-1]
hy_now = hy.iloc[-1]

# Higher warmth = less fear / tighter credit.
vix_warmth = 100 - percentile_rank(vix, vix_now)
hy_oas_warmth = 100 - percentile_rank(hy, hy_now)

ma200 = spy.rolling(200).mean()
dist200 = (spy / ma200 - 1).dropna()
trend_warmth = percentile_rank(dist200, dist200.iloc[-1])

mom63 = (spy / spy.shift(63) - 1).dropna()
momentum_warmth = percentile_rank(mom63, mom63.iloc[-1])

vals = [vix_warmth, hy_oas_warmth, trend_warmth, momentum_warmth]
proxy_score = float(np.nanmean(vals))

if proxy_score < 25:
    proxy_stage = "PESSIMISM"
elif proxy_score < 50:
    proxy_stage = "SKEPTICISM"
elif proxy_score < 75:
    proxy_stage = "OPTIMISM"
else:
    proxy_stage = "EUPHORIA"

manual = pd.read_csv(MANUAL / "sentiment_optional_inputs.csv")
manual_available = len(manual.dropna(how="all")) > 0

latest = pd.DataFrame([{
    "as_of": max(vix.index.max(), hy.index.max(), spy.index.max()).date().isoformat(),
    "proxy_score": proxy_score,
    "proxy_stage": proxy_stage,
    "vix_warmth": vix_warmth,
    "hy_oas_warmth": hy_oas_warmth,
    "spy_trend_warmth": trend_warmth,
    "spy_momentum_warmth": momentum_warmth,
    "manual_overlay_available": bool(manual_available),
    "warning": "Market-implied proxy only; do not treat as Ken Fisher's exact sentiment-stage model."
}])
latest.to_csv(OUT / "sentiment_market_proxy_latest.csv", index=False)
print("Sentiment proxy updated.")

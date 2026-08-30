
from pathlib import Path
from io import StringIO
import numpy as np
import pandas as pd
import requests
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
RAW.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)

CONSTITUENTS_URL = (
    "https://raw.githubusercontent.com/"
    "datasets/s-and-p-500-companies/refs/heads/main/data/constituents.csv"
)
CACHE = RAW / "sp500_constituents.csv"

SECTOR_ETF = {
    "Information Technology": "XLK",
    "Financials": "XLF",
    "Industrials": "XLI",
    "Energy": "XLE",
    "Materials": "XLB",
    "Consumer Discretionary": "XLY",
    "Consumer Staples": "XLP",
    "Health Care": "XLV",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Communication Services": "XLC",
}

SECTOR_KO = {
    "Information Technology": "기술",
    "Financials": "금융",
    "Industrials": "산업재",
    "Energy": "에너지",
    "Materials": "소재",
    "Consumer Discretionary": "경기소비재",
    "Consumer Staples": "필수소비재",
    "Health Care": "헬스케어",
    "Utilities": "유틸리티",
    "Real Estate": "부동산",
    "Communication Services": "커뮤니케이션서비스",
}


def load_constituents():
    try:
        r = requests.get(
            CONSTITUENTS_URL,
            timeout=30,
            headers={"User-Agent": "market-leadership-dashboard/1.0"},
        )
        r.raise_for_status()
        df = pd.read_csv(StringIO(r.text))
        need = ["Symbol", "Security", "GICS Sector", "GICS Sub-Industry"]
        miss = [c for c in need if c not in df.columns]
        if miss:
            raise ValueError(f"Missing columns: {miss}")
        df = df[need].copy()
        df["yf_symbol"] = df["Symbol"].astype(str).str.replace(".", "-", regex=False)
        df.to_csv(CACHE, index=False)
        return df
    except Exception as exc:
        if CACHE.exists():
            print(f"WARNING: constituents refresh failed ({exc}); using cache.")
            df = pd.read_csv(CACHE)
            if "yf_symbol" not in df.columns:
                df["yf_symbol"] = df["Symbol"].astype(str).str.replace(".", "-", regex=False)
            return df
        raise


def download_close(tickers, period="3y", batch_size=80):
    parts = []
    tickers = list(dict.fromkeys(tickers))
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i+batch_size]
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
        return pd.DataFrame()
    close = pd.concat(parts, axis=1)
    close = close.loc[:, ~close.columns.duplicated()].sort_index()
    close.index = pd.to_datetime(close.index).tz_localize(None)
    return close


def trailing_return(series, pos, n):
    if pos < n:
        return np.nan
    p1 = series.iloc[pos]
    p0 = series.iloc[pos-n]
    if pd.isna(p1) or pd.isna(p0) or p0 == 0:
        return np.nan
    return float(p1 / p0 - 1)


def main():
    const = load_constituents()
    stock_tickers = const["yf_symbol"].dropna().drop_duplicates().tolist()
    market_tickers = ["SPY"] + list(SECTOR_ETF.values())

    close = download_close(stock_tickers + market_tickers, period="3y")
    if close.empty or "SPY" not in close.columns:
        raise RuntimeError("Price download failed.")

    stock_cols = [t for t in stock_tickers if t in close.columns]
    close[stock_cols].to_csv(RAW / "sp500_close_wide.csv", index_label="date")

    windows = [21, 63, 126, 252]
    dates = close.index[-160:]
    market_rows = []
    sector_rows = []

    symbol_sector = const.set_index("yf_symbol")["GICS Sector"].to_dict()

    for dt in dates:
        pos = close.index.get_loc(dt)

        # Market breadth.
        for n in windows:
            if pos < n:
                continue
            spy_r = trailing_return(close["SPY"], pos, n)
            vals = []
            for t in stock_cols:
                rr = trailing_return(close[t], pos, n)
                if pd.notna(rr):
                    vals.append(rr)
            if len(vals) >= 300 and pd.notna(spy_r):
                arr = np.array(vals, dtype=float)
                market_rows.append({
                    "date": dt.date().isoformat(),
                    "window": n,
                    "breadth_pct": float((arr > spy_r).mean()),
                    "n_valid": int(len(arr)),
                    "definition":"Percent of current S&P 500 constituents outperforming SPY",
                })

        # Intra-sector breadth / dispersion.
        for gics, etf in SECTOR_ETF.items():
            if etf not in close.columns:
                continue
            members = [t for t in stock_cols if symbol_sector.get(t) == gics]
            for n in windows:
                if pos < n:
                    continue
                spy_r = trailing_return(close["SPY"], pos, n)
                etf_r = trailing_return(close[etf], pos, n)
                vals = []
                for t in members:
                    rr = trailing_return(close[t], pos, n)
                    if pd.notna(rr):
                        vals.append(rr)
                min_required = max(5, int(len(members) * 0.55))
                if len(vals) < min_required or pd.isna(spy_r) or pd.isna(etf_r):
                    continue

                arr = np.array(vals, dtype=float)
                sector_rows.append({
                    "date": dt.date().isoformat(),
                    "ticker": etf,
                    "gics_sector": gics,
                    "sector_ko": SECTOR_KO[gics],
                    "window": n,
                    "breadth_vs_spy_pct": float((arr > spy_r).mean()),
                    "breadth_vs_sector_pct": float((arr > etf_r).mean()),
                    "median_excess_vs_spy": float(np.nanmedian(arr - spy_r)),
                    "median_excess_vs_sector": float(np.nanmedian(arr - etf_r)),
                    "dispersion_std": float(np.nanstd(arr, ddof=1)) if len(arr) > 1 else np.nan,
                    "n_valid": int(len(arr)),
                    "n_sector_members": int(len(members)),
                    "coverage": float(len(arr) / len(members)) if members else np.nan,
                    "survivorship_note":"Uses current S&P 500 constituents",
                })

    market_hist = pd.DataFrame(market_rows)
    sector_hist = pd.DataFrame(sector_rows)
    if market_hist.empty:
        raise RuntimeError("Market breadth calculation returned 0 rows.")

    market_hist.to_csv(OUT/"breadth_history.csv", index=False)
    market_latest = (
        market_hist.sort_values("date")
        .groupby("window", as_index=False)
        .tail(1)
        .rename(columns={"date":"as_of"})
    )
    market_latest.to_csv(OUT/"breadth_latest.csv", index=False)

    if not sector_hist.empty:
        sector_hist.to_csv(OUT/"sector_internal_breadth_history.csv", index=False)
        latest_date = sector_hist["date"].max()
        latest = sector_hist[sector_hist["date"].eq(latest_date)].copy()

        # Same-window change versus approximately one trading month ago.
        hist_dates = sorted(sector_hist["date"].unique())
        prior_date = hist_dates[-22] if len(hist_dates) >= 22 else hist_dates[0]
        prior = sector_hist[sector_hist["date"].eq(prior_date)][
            ["ticker","window","breadth_vs_spy_pct","breadth_vs_sector_pct","dispersion_std"]
        ].copy()
        prior = prior.rename(columns={
            "breadth_vs_spy_pct":"breadth_vs_spy_pct_1m_ago",
            "breadth_vs_sector_pct":"breadth_vs_sector_pct_1m_ago",
            "dispersion_std":"dispersion_std_1m_ago",
        })
        latest = latest.merge(prior, on=["ticker","window"], how="left")
        latest["breadth_vs_spy_change_1m"] = (
            latest["breadth_vs_spy_pct"] - latest["breadth_vs_spy_pct_1m_ago"]
        )
        latest["breadth_vs_sector_change_1m"] = (
            latest["breadth_vs_sector_pct"] - latest["breadth_vs_sector_pct_1m_ago"]
        )
        latest["dispersion_change_1m"] = (
            latest["dispersion_std"] - latest["dispersion_std_1m_ago"]
        )
        latest = latest.rename(columns={"date":"as_of"})
        latest.to_csv(OUT/"sector_internal_breadth_latest.csv", index=False)

    print(
        f"Breadth updated: market rows={len(market_hist)}, "
        f"sector-internal rows={len(sector_hist)}"
    )


if __name__ == "__main__":
    main()

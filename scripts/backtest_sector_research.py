from pathlib import Path
from io import BytesIO, StringIO
import csv
import json
import os
import time
import zipfile
import numpy as np
import pandas as pd
import requests
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "research_validation"
OUT = ROOT / "data" / "processed"
RAW.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)

FF49_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/49_Industry_Portfolios_CSV.zip"
SECTORS = ["XLK","XLF","XLI","XLE","XLB","XLY","XLP","XLV","XLU","XLRE","XLC"]


def compound(x):
    x = pd.Series(x, dtype=float).dropna()
    if len(x) == 0:
        return np.nan
    return float((1 + x).prod() - 1)


def recent_compound(series, months):
    x = series.dropna()
    if len(x) < months:
        return np.nan
    return compound(x.iloc[-months:])


def formation_window(series, start_lag, end_lag):
    """Monthly return compounded from start_lag months ago through end_lag months ago, inclusive."""
    x = series.dropna()
    if len(x) < start_lag:
        return np.nan
    # Example start_lag=12,end_lag=2 -> months t-11 ... t-1 in zero-index convention.
    vals = x.iloc[-start_lag: -end_lag + 1 if end_lag > 1 else None]
    return compound(vals)


def fwd_compound(series, pos, months):
    vals = series.iloc[pos+1:pos+1+months]
    if len(vals) < months or vals.isna().any():
        return np.nan
    return compound(vals)


def percentile_rank(row, ascending=False):
    return row.rank(pct=True, ascending=ascending, method="average")


def summarize_events(events, group_cols):
    if events.empty:
        return pd.DataFrame()
    rows = []
    for keys, g in events.groupby(group_cols, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        base = dict(zip(group_cols, keys))
        for horizon in [3,6,12]:
            c = f"forward_alpha_{horizon}m"
            x = pd.to_numeric(g[c], errors="coerce").dropna()
            if x.empty:
                continue
            row = dict(base)
            row.update({
                "horizon_months": horizon,
                "n_events": int(len(x)),
                "mean_alpha": float(x.mean()),
                "median_alpha": float(x.median()),
                "outperform_probability": float((x > 0).mean()),
                "q25_alpha": float(x.quantile(.25)),
                "q75_alpha": float(x.quantile(.75)),
            })
            rows.append(row)
    return pd.DataFrame(rows)


def etf_validation(force=False):
    summary_path = OUT / "sector_rule_backtest_summary.csv"
    if summary_path.exists() and not force and (time.time() - summary_path.stat().st_mtime) < 25*86400:
        print("ETF backtest fresh; skipped.")
        return

    d = yf.download(
        ["SPY"] + SECTORS,
        period="max",
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=True,
        group_by="column",
    )
    if d.empty:
        print("ETF backtest download failed.")
        return
    close = d["Close"] if isinstance(d.columns, pd.MultiIndex) else d
    close.index = pd.to_datetime(close.index).tz_localize(None)
    monthly_px = close.resample("ME").last().dropna(how="all")
    monthly = monthly_px.pct_change(fill_method=None)
    if "SPY" not in monthly.columns:
        return

    sector_cols = [s for s in SECTORS if s in monthly.columns]
    rel_monthly = (1 + monthly[sector_cols]).div(1 + monthly["SPY"], axis=0) - 1

    events = []
    for i in range(13, len(monthly)-12):
        date = monthly.index[i]
        hist = monthly.iloc[:i+1]
        rel_hist = rel_monthly.iloc[:i+1]

        metrics = pd.DataFrame(index=sector_cols)
        metrics["mom_1"] = [compound(rel_hist[s].iloc[-1:]) for s in sector_cols]
        metrics["mom_3"] = [compound(rel_hist[s].iloc[-3:]) for s in sector_cols]
        metrics["mom_6"] = [compound(rel_hist[s].iloc[-6:]) for s in sector_cols]
        metrics["mom_12"] = [compound(rel_hist[s].iloc[-12:]) for s in sector_cols]
        metrics["mom_12_1"] = [compound(rel_hist[s].iloc[-12:-1]) for s in sector_cols]
        metrics["mom_12_7"] = [compound(rel_hist[s].iloc[-12:-6]) for s in sector_cols]
        metrics["consistency"] = [(rel_hist[s].iloc[-12:] > 0).mean() for s in sector_cols]

        for c in metrics.columns:
            metrics[f"rank_{c}"] = metrics[c].rank(ascending=False, method="min")

        n = len(metrics)
        top = max(2, int(np.ceil(n*0.30)))
        low_start = int(np.floor(n*0.55)) + 1

        # Market rebound context and prior relative loser status.
        spy_px = monthly_px["SPY"].iloc[max(0,i-12):i+1]
        spy_dd = float((spy_px / spy_px.cummax() - 1).min()) if len(spy_px) else np.nan
        market_rebound = compound(monthly["SPY"].iloc[max(0,i-2):i+1])

        # Prior 12m sector drawdowns ending 3 months ago.
        dd = {}
        for s in sector_cols:
            px = monthly_px[s].iloc[max(0,i-15):max(0,i-2)]
            dd[s] = float((px / px.cummax() - 1).min()) if len(px) >= 4 else np.nan
        dd_rank = pd.Series(dd).rank(ascending=True, method="min")

        for s, rr in metrics.iterrows():
            bounce = (
                pd.notna(spy_dd) and spy_dd <= -0.10 and pd.notna(market_rebound) and market_rebound > 0
                and dd_rank.get(s, 99) <= top
                and rr["rank_mom_3"] <= top
                and rr["rank_mom_12_1"] >= low_start
            )

            if rr["rank_mom_12"] <= top and rr["rank_mom_3"] >= low_start and rr["rank_mom_1"] >= low_start:
                state = "DECAY"
            elif rr["rank_mom_1"] <= top and rr["rank_mom_3"] >= low_start:
                state = "NOISE"
            elif bounce:
                state = "BOUNCE"
            elif (
                rr["rank_mom_3"] <= top
                and rr["rank_mom_6"] <= max(top+1, int(np.ceil(n*.45)))
                and rr["rank_mom_12_1"] <= top
                and rr["consistency"] >= metrics["consistency"].median()
            ):
                state = "CONSIDER"
            elif rr["rank_mom_3"] <= max(top+1, int(np.ceil(n*.45))) and rr["mom_3"] > 0:
                state = "WATCH"
            else:
                state = "NEUTRAL"

            ev = {
                "date": date.date().isoformat(), "ticker": s, "state": state,
                "mom_1": rr["mom_1"], "mom_3": rr["mom_3"], "mom_6": rr["mom_6"],
                "mom_12_1": rr["mom_12_1"], "mom_12_7": rr["mom_12_7"],
                "consistency": rr["consistency"], "market_prior_drawdown": spy_dd,
            }
            for h in [3,6,12]:
                sr = fwd_compound(monthly[s], i, h)
                br = fwd_compound(monthly["SPY"], i, h)
                ev[f"forward_alpha_{h}m"] = sr - br if pd.notna(sr) and pd.notna(br) else np.nan
            events.append(ev)

    evdf = pd.DataFrame(events)
    evdf.to_csv(OUT / "sector_rule_backtest_events.csv", index=False)
    sm = summarize_events(evdf, ["state"])
    sm["validation"] = "Select Sector SPDR historical ETF event study"
    sm["rule_note"] = "Literature-informed fixed specification; not parameter-optimized"
    sm.to_csv(summary_path, index=False)
    print("ETF rule backtest updated", len(evdf), "events")


def parse_ff49_monthly(raw_zip):
    z = zipfile.ZipFile(BytesIO(raw_zip))
    name = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
    txt = z.read(name).decode("latin-1", errors="ignore")
    lines = txt.splitlines()

    header_idx = None
    for i, line in enumerate(lines):
        # First monthly value-weighted table header begins with a blank first cell and industry names.
        if "Agric" in line and "Food" in line and "," in line:
            header_idx = i
            break
    if header_idx is None:
        raise RuntimeError("Could not find FF49 monthly header")

    reader = csv.reader(lines[header_idx:])
    header = next(reader)
    cols = [c.strip() for c in header]
    rows = []
    for rec in reader:
        if not rec or not rec[0].strip():
            break
        key = rec[0].strip()
        if not (len(key) == 6 and key.isdigit()):
            break
        vals = [key] + rec[1:len(cols)]
        rows.append(vals)

    df = pd.DataFrame(rows, columns=["date"] + cols[1:])
    df["date"] = pd.to_datetime(df["date"], format="%Y%m") + pd.offsets.MonthEnd(0)
    for c in df.columns[1:]:
        df[c] = pd.to_numeric(df[c], errors="coerce") / 100.0
        df.loc[df[c] <= -0.90, c] = np.nan  # French missing codes -99.99/-999
    return df.set_index("date")


def ff49_validation(force=False):
    outp = OUT / "ff49_research_validation.csv"
    if outp.exists() and not force and (time.time() - outp.stat().st_mtime) < 25*86400:
        print("FF49 validation fresh; skipped.")
        return

    cache = RAW / "49_Industry_Portfolios_CSV.zip"
    if cache.exists() and (time.time() - cache.stat().st_mtime) < 30*86400:
        raw = cache.read_bytes()
    else:
        r = requests.get(FF49_URL, timeout=60, headers={"User-Agent":"market-leadership-dashboard/1.0"})
        r.raise_for_status()
        raw = r.content
        cache.write_bytes(raw)

    ret = parse_ff49_monthly(raw)
    industries = ret.columns.tolist()
    benchmark = ret.mean(axis=1, skipna=True)
    rel = (1 + ret).div(1 + benchmark, axis=0) - 1

    signals = {"mom_3":3, "mom_6":6}
    events = []
    for i in range(13, len(ret)-12):
        date = ret.index[i]
        sig = pd.DataFrame(index=industries)
        sig["mom_3"] = [compound(rel[s].iloc[i-2:i+1]) for s in industries]
        sig["mom_6"] = [compound(rel[s].iloc[i-5:i+1]) for s in industries]
        sig["mom_12_1"] = [compound(rel[s].iloc[i-11:i]) for s in industries]
        sig["mom_12_7"] = [compound(rel[s].iloc[i-11:i-5]) for s in industries]
        sig["consistency_12"] = [(rel[s].iloc[i-11:i+1] > 0).mean() for s in industries]

        for signal in sig.columns:
            ranked = sig[signal].rank(pct=True, ascending=True)
            top_names = ranked[ranked >= 0.80].index
            for s in top_names:
                ev = {"date":date.date().isoformat(), "industry":s, "signal":signal, "formation_value":sig.loc[s,signal]}
                for h in [3,6,12]:
                    sr = fwd_compound(ret[s], i, h)
                    br = fwd_compound(benchmark, i, h)
                    ev[f"forward_alpha_{h}m"] = sr - br if pd.notna(sr) and pd.notna(br) else np.nan
                events.append(ev)

    ev = pd.DataFrame(events)
    summary = summarize_events(ev, ["signal"])
    summary["validation"] = "Kenneth French 49 Industry Portfolios"
    summary["selection_rule"] = "Top quintile by pre-specified signal; cross-sectional equal-weight industry benchmark"
    summary["data_start"] = ret.index.min().date().isoformat()
    summary["data_end"] = ret.index.max().date().isoformat()
    summary.to_csv(outp, index=False)
    ev.to_csv(OUT / "ff49_research_validation_events.csv", index=False)
    print("FF49 validation updated", len(ev), "events")


def main():
    force = os.getenv("FORCE_RESEARCH_BACKTEST", "0") == "1"
    try:
        etf_validation(force)
    except Exception as exc:
        print("ETF validation failed:", exc)
    try:
        ff49_validation(force)
    except Exception as exc:
        print("FF49 validation failed:", exc)


if __name__ == "__main__":
    main()


from pathlib import Path
import math
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
CFG = ROOT / "config"
OUT.mkdir(parents=True, exist_ok=True)

PRICE_FILE = RAW / "prices_close_wide.csv"
INST_FILE = CFG / "instruments.csv"

if not PRICE_FILE.exists():
    raise FileNotFoundError(f"Missing {PRICE_FILE}")
if not INST_FILE.exists():
    raise FileNotFoundError(f"Missing {INST_FILE}")

close = pd.read_csv(PRICE_FILE, parse_dates=["date"], index_col="date").sort_index()
inst = pd.read_csv(INST_FILE)
rets = close.pct_change(fill_method=None)

TRADING = {"21":21, "63":63, "126":126, "252":252, "756":756}
SKIP_1M = 21
START_12M = 252
END_7M = 147


def trailing_return(s, n):
    x = s.dropna()
    if len(x) <= n:
        return np.nan
    return float(x.iloc[-1] / x.iloc[-(n+1)] - 1)


def between_return(s, old_days, recent_days):
    x = s.dropna()
    if len(x) <= old_days:
        return np.nan
    p0 = x.iloc[-(old_days+1)]
    p1 = x.iloc[-(recent_days+1)] if recent_days > 0 else x.iloc[-1]
    if pd.isna(p0) or pd.isna(p1) or p0 == 0:
        return np.nan
    return float(p1/p0 - 1)


def freq_and_magnitude(a, b, n):
    d = pd.concat([a,b], axis=1).dropna().tail(n)
    if d.empty:
        return np.nan, np.nan
    diff = d.iloc[:,0] - d.iloc[:,1]
    return float((diff > 0).mean()), float(diff.mean())


def monthly_consistency(a_px, b_px, months=12):
    d = pd.concat([a_px,b_px], axis=1).dropna()
    if len(d) < 80:
        return np.nan, np.nan
    monthly = d.resample("ME").last().pct_change(fill_method=None).dropna()
    if len(monthly) < min(6, months):
        return np.nan, np.nan
    rel = ((1+monthly.iloc[:,0])/(1+monthly.iloc[:,1])-1).tail(months)
    return float((rel > 0).mean()), float(rel.mean())


def max_drawdown(s):
    x = s.dropna()
    if len(x) < 2:
        return np.nan
    return float((x/x.cummax()-1).min())


def slice_by_days(s, start_days_ago, end_days_ago):
    x = s.dropna()
    if len(x) <= start_days_ago:
        return pd.Series(dtype=float)
    left = -(start_days_ago+1)
    right = None if end_days_ago == 0 else -end_days_ago
    return x.iloc[left:right]


def current_drawdown(s):
    x = s.dropna()
    if len(x) < 2:
        return np.nan
    return float(x.iloc[-1] / x.cummax().iloc[-1] - 1)


def snapshot_group(group_name, dt):
    g = inst[inst["group"].eq(group_name)][["ticker","subgroup","benchmark"]].copy()
    c = close.loc[:dt]
    r = rets.loc[:dt]
    rows = []

    for _, meta in g.iterrows():
        t, bench = meta["ticker"], meta["benchmark"]
        if t not in c.columns or bench not in c.columns:
            continue

        row = {
            "as_of": pd.Timestamp(dt).date().isoformat(),
            "ticker": t,
            "sector": meta["subgroup"],
            "benchmark": bench,
        }

        for label,n in TRADING.items():
            tr, br = trailing_return(c[t],n), trailing_return(c[bench],n)
            row[f"return_{label}"] = tr
            row[f"benchmark_return_{label}"] = br
            row[f"excess_{label}"] = tr-br if pd.notna(tr) and pd.notna(br) else np.nan
            f,m = freq_and_magnitude(r[t],r[bench],n)
            row[f"freq_{label}"] = f
            row[f"magnitude_{label}"] = m

        tr,br = between_return(c[t],252,21), between_return(c[bench],252,21)
        row["return_12_1"],row["benchmark_return_12_1"] = tr,br
        row["excess_12_1"] = tr-br if pd.notna(tr) and pd.notna(br) else np.nan

        tr,br = between_return(c[t],252,147), between_return(c[bench],252,147)
        row["return_12_7"],row["benchmark_return_12_7"] = tr,br
        row["excess_12_7"] = tr-br if pd.notna(tr) and pd.notna(br) else np.nan

        cons,mmag = monthly_consistency(c[t],c[bench],12)
        row["consistency_12m"] = cons
        row["monthly_rel_magnitude_12m"] = mmag

        prior_t = slice_by_days(c[t],315,63)
        prior_b = slice_by_days(c[bench],315,63)
        row["prior_drawdown_252_ex63"] = max_drawdown(prior_t)
        row["benchmark_prior_drawdown_252_ex63"] = max_drawdown(prior_b)
        row["benchmark_current_drawdown"] = current_drawdown(c[bench])
        row["rebound_63"] = trailing_return(c[t],63)
        row["benchmark_rebound_63"] = trailing_return(c[bench],63)
        rows.append(row)

    out = pd.DataFrame(rows)
    if out.empty:
        return out

    rank_metrics = [
        "excess_21","excess_63","excess_126","excess_252","excess_756",
        "excess_12_1","excess_12_7","consistency_12m",
    ]
    for col in rank_metrics:
        if col in out.columns:
            out[f"rank_{col.replace('excess_','')}"] = (
                pd.to_numeric(out[col],errors="coerce")
                .rank(ascending=False,method="min")
                .astype("Int64")
            )

    out["rank_prior_drawdown"] = (
        pd.to_numeric(out["prior_drawdown_252_ex63"],errors="coerce")
        .rank(ascending=True,method="min").astype("Int64")
    )
    out["rank_rebound_63"] = (
        pd.to_numeric(out["rebound_63"],errors="coerce")
        .rank(ascending=False,method="min").astype("Int64")
    )

    n=len(out)
    top_n=max(2,math.ceil(n*0.30))
    low_start=max(top_n+1,math.floor(n*0.55)+1)

    def bounce_flag(rr):
        market_panic = (
            pd.notna(rr["benchmark_prior_drawdown_252_ex63"])
            and rr["benchmark_prior_drawdown_252_ex63"] <= -0.10
            and pd.notna(rr["benchmark_rebound_63"])
            and rr["benchmark_rebound_63"] > 0
        )
        deep_loser = pd.notna(rr["rank_prior_drawdown"]) and rr["rank_prior_drawdown"] <= top_n
        rebound_leader = pd.notna(rr["rank_rebound_63"]) and rr["rank_rebound_63"] <= top_n
        intermediate_weak = (
            pd.isna(rr.get("rank_12_1"))
            or rr.get("rank_12_1") > low_start
            or (pd.notna(rr.get("excess_12_1")) and rr.get("excess_12_1") <= 0)
        )
        return bool(market_panic and deep_loser and rebound_leader and intermediate_weak)

    out["bounce_flag_research"] = out.apply(bounce_flag,axis=1)

    def old_leader_failure(rr):
        long_leader = (
            (pd.notna(rr.get("rank_252")) and rr.get("rank_252") <= top_n)
            or (pd.notna(rr.get("rank_756")) and rr.get("rank_756") <= top_n)
        )
        current_weak = (
            pd.notna(rr.get("rank_63")) and rr.get("rank_63") > low_start
            and pd.notna(rr.get("rank_21")) and rr.get("rank_21") > low_start
            and pd.notna(rr.get("excess_63")) and rr.get("excess_63") < 0
        )
        recovered = (
            pd.notna(rr.get("benchmark_current_drawdown"))
            and rr.get("benchmark_current_drawdown") >= -0.05
        )
        return bool(long_leader and current_weak and recovered)

    out["old_leader_failure_flag"] = out.apply(old_leader_failure,axis=1)
    out["rank_improvement_126_to_63"] = (
        pd.to_numeric(out["rank_126"],errors="coerce")
        - pd.to_numeric(out["rank_63"],errors="coerce")
    )
    return out


def write_group(group_name, latest_name, history_name):
    dt=close.index.max()
    latest=snapshot_group(group_name,dt)
    latest.to_csv(OUT/latest_name,index=False)

    month_ends=(
        pd.Series(close.index,index=close.index.to_period("M"))
        .groupby(level=0).max().tolist()
    )[-72:]
    hist=[]
    for d in month_ends:
        part=snapshot_group(group_name,d)
        if len(part):
            hist.append(part)
    pd.concat(hist,ignore_index=True).to_csv(OUT/history_name,index=False) if hist else pd.DataFrame().to_csv(OUT/history_name,index=False)
    print(group_name, "latest", len(latest), "history months", len(hist))


def main():
    write_group("sector","sector_research_features_latest.csv","sector_research_features_history.csv")
    write_group("global_sector","global_sector_research_features_latest.csv","global_sector_research_features_history.csv")
    write_group("region","region_research_features_latest.csv","region_research_features_history.csv")


if __name__=="__main__":
    main()

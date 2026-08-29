from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
CFG = ROOT / "config"
OUT.mkdir(parents=True, exist_ok=True)

close = pd.read_csv(RAW / "prices_close_wide.csv", parse_dates=["date"], index_col="date").sort_index()
rets = close.pct_change(fill_method=None)
pairs = pd.read_csv(CFG / "pairs.csv")
inst = pd.read_csv(CFG / "instruments.csv")
baskets = pd.read_csv(CFG / "baskets.csv")
windows = [21, 63, 126]

# Build equal-weight basket price indices from daily constituent returns.
for basket_id, g in baskets.groupby("basket_id"):
    members = [t for t in g["ticker"] if t in rets.columns]
    weights = g.set_index("ticker").loc[members, "weight"].astype(float)
    weights = weights / weights.sum()
    bret = rets[members].mul(weights, axis=1).sum(axis=1, min_count=1)
    bpx = (1 + bret.fillna(0)).cumprod() * 100
    close[basket_id.upper()] = bpx
    rets[basket_id.upper()] = bret

# Add cyclical/defensive synthetic pair.
extra_pair = pd.DataFrame([{
    "pair_id":"cyclical_defensive",
    "numerator":"CYCLICAL",
    "denominator":"DEFENSIVE",
    "leader_when_ratio_rises":"Cyclical",
    "leader_when_ratio_falls":"Defensive",
    "priority":1,
    "logic":"Equal-weight US cyclical basket versus defensive basket."
}])
pairs = pd.concat([pairs, extra_pair], ignore_index=True)

def cumret(s, n):
    x = s.dropna()
    if len(x) <= n:
        return np.nan
    return x.iloc[-1] / x.iloc[-(n+1)] - 1

def freq_last(a, b, n, mask=None):
    df = pd.concat([a, b], axis=1).dropna()
    if mask is not None:
        df = df[mask.reindex(df.index).fillna(False)]
    df = df.tail(n)
    if len(df) == 0:
        return np.nan
    return float((df.iloc[:,0] > df.iloc[:,1]).mean())

def avg_diff_last(a, b, n, mask=None):
    df = pd.concat([a, b], axis=1).dropna()
    if mask is not None:
        df = df[mask.reindex(df.index).fillna(False)]
    df = df.tail(n)
    if len(df) == 0:
        return np.nan
    return float((df.iloc[:,0] - df.iloc[:,1]).mean())

def max_drawdown(s, n=252):
    x = s.dropna().tail(n)
    if len(x) < 2:
        return np.nan
    dd = x / x.cummax() - 1
    return float(dd.min())

def rebound_from_low(s, n=126):
    x = s.dropna().tail(n)
    if len(x) < 2:
        return np.nan
    return float(x.iloc[-1] / x.min() - 1)

as_of = close.index.max().date().isoformat()
spy_up = rets["SPY"] > 0
spy_down = rets["SPY"] < 0

# ---------- Style / cross-market pairs ----------
style_rows = []
for _, p in pairs.iterrows():
    num, den = p["numerator"], p["denominator"]
    if num not in close.columns or den not in close.columns:
        continue
    ratio = close[num] / close[den]
    row = {"as_of":as_of,"pair_id":p["pair_id"],"numerator":num,"denominator":den}
    leaders = {}
    for n in windows:
        rr = cumret(ratio, n)
        leader = p["leader_when_ratio_rises"] if (pd.notna(rr) and rr >= 0) else p["leader_when_ratio_falls"]
        leaders[n] = leader
        row[f"leader_{n}"] = leader
        row[f"rs_return_{n}"] = rr
        row[f"freq_{n}"] = freq_last(rets[num], rets[den], n)
        row[f"magnitude_{n}"] = avg_diff_last(rets[num], rets[den], n)
        row[f"upday_freq_{n}"] = freq_last(rets[num], rets[den], n, spy_up)
        row[f"upday_magnitude_{n}"] = avg_diff_last(rets[num], rets[den], n, spy_up)
        row[f"downday_freq_{n}"] = freq_last(rets[num], rets[den], n, spy_down)
        row[f"downday_magnitude_{n}"] = avg_diff_last(rets[num], rets[den], n, spy_down)

    if leaders.get(21) == leaders.get(63) == leaders.get(126):
        state = "STABLE"
    elif leaders.get(21) != leaders.get(63):
        f = row.get("freq_21", np.nan)
        strength = f if leaders[21] == p["leader_when_ratio_rises"] else (1-f if pd.notna(f) else np.nan)
        state = "ROTATING" if pd.notna(strength) and strength >= 0.60 else "WATCH"
    elif leaders.get(21) == leaders.get(63) and leaders.get(63) != leaders.get(126):
        state = "CONFIRMED"
    else:
        state = "WATCH"
    row["change_state"] = state
    style_rows.append(row)

pd.DataFrame(style_rows).to_csv(OUT/"style_leadership_latest.csv", index=False)

# Recent history ~= 6 months
hist_dates = close.index[-140:]
style_hist = []
for dt in hist_dates:
    c = close.loc[:dt]
    r = rets.loc[:dt]
    up = r["SPY"] > 0
    down = r["SPY"] < 0
    for _, p in pairs.iterrows():
        num, den = p["numerator"], p["denominator"]
        if num not in c.columns or den not in c.columns:
            continue
        ratio = c[num] / c[den]
        item = {"date":dt.date().isoformat(),"pair_id":p["pair_id"]}
        for n in windows:
            item[f"rs_return_{n}"] = cumret(ratio, n)
            item[f"freq_{n}"] = freq_last(r[num], r[den], n)
            item[f"magnitude_{n}"] = avg_diff_last(r[num], r[den], n)
            item[f"upday_freq_{n}"] = freq_last(r[num], r[den], n, up)
            item[f"upday_magnitude_{n}"] = avg_diff_last(r[num], r[den], n, up)
            item[f"downday_freq_{n}"] = freq_last(r[num], r[den], n, down)
            item[f"downday_magnitude_{n}"] = avg_diff_last(r[num], r[den], n, down)
        style_hist.append(item)
pd.DataFrame(style_hist).to_csv(OUT/"style_leadership_history.csv", index=False)

def build_group(group_name, latest_name, history_name):
    gdf = inst[inst["group"] == group_name][["ticker","subgroup","benchmark"]].copy()
    latest_rows = []
    for _, s in gdf.iterrows():
        t, bench = s["ticker"], s["benchmark"]
        if t not in close.columns or bench not in close.columns:
            continue
        row = {"as_of":as_of,"ticker":t,"sector":s["subgroup"],"benchmark":bench}
        for n in windows:
            tr = cumret(close[t], n)
            br = cumret(close[bench], n)
            row[f"return_{n}"] = tr
            row[f"excess_{n}"] = tr-br if pd.notna(tr) and pd.notna(br) else np.nan
            row[f"freq_{n}"] = freq_last(rets[t], rets[bench], n)
            row[f"magnitude_{n}"] = avg_diff_last(rets[t], rets[bench], n)
        latest_rows.append(row)

    latest = pd.DataFrame(latest_rows)
    if not latest.empty:
        for n in windows:
            latest[f"rank_{n}"] = latest[f"excess_{n}"].rank(ascending=False, method="min").astype("Int64")
        latest["rank_change_21_vs_63"] = latest["rank_63"] - latest["rank_21"]

        def trend_label(r):
            if pd.isna(r["rank_21"]) or pd.isna(r["rank_63"]):
                return "N/A"
            if r["rank_change_21_vs_63"] >= 3 and r["freq_21"] >= 0.55:
                return "EMERGING"
            if r["rank_change_21_vs_63"] <= -3:
                return "WEAKENING"
            if r["rank_21"] <= 3 and r["rank_63"] <= 3:
                return "LEADER"
            return "NEUTRAL"
        latest["trend_label"] = latest.apply(trend_label, axis=1)
        latest = latest.sort_values(["rank_21","rank_63"])
    latest.to_csv(OUT/latest_name, index=False)

    history = []
    for dt in hist_dates:
        c = close.loc[:dt]
        r = rets.loc[:dt]
        day_rows = []
        for _, s in gdf.iterrows():
            t, bench = s["ticker"], s["benchmark"]
            if t not in c.columns or bench not in c.columns:
                continue
            item = {"date":dt.date().isoformat(),"ticker":t,"sector":s["subgroup"],"benchmark":bench}
            for n in windows:
                tr = cumret(c[t], n)
                br = cumret(c[bench], n)
                item[f"excess_{n}"] = tr-br if pd.notna(tr) and pd.notna(br) else np.nan
                item[f"freq_{n}"] = freq_last(r[t], r[bench], n)
                item[f"magnitude_{n}"] = avg_diff_last(r[t], r[bench], n)
            day_rows.append(item)
        day = pd.DataFrame(day_rows)
        if not day.empty:
            for n in windows:
                day[f"rank_{n}"] = day[f"excess_{n}"].rank(ascending=False, method="min")
            history.append(day)
    if history:
        pd.concat(history, ignore_index=True).to_csv(OUT/history_name, index=False)
    else:
        pd.DataFrame().to_csv(OUT/history_name, index=False)

build_group("sector","sector_leadership_latest.csv","sector_leadership_history.csv")
build_group("global_sector","global_sector_leadership_latest.csv","global_sector_leadership_history.csv")
build_group("region","region_leadership_latest.csv","region_leadership_history.csv")

# ---------- Mechanical market regime context ----------
spy = close["SPY"].dropna()
ath = spy.cummax()
dd = spy / ath - 1
last_peak_date = spy.loc[spy == ath].index.max()
days_since_peak = int((spy.index.max() - last_peak_date).days)
ma200 = spy.rolling(200).mean()
drawdown = float(dd.iloc[-1])

if drawdown <= -0.20:
    mechanical_state = "BEAR_DRAWDOWN"
elif drawdown <= -0.10:
    mechanical_state = "CORRECTION"
elif spy.iloc[-1] >= ma200.iloc[-1]:
    mechanical_state = "ADVANCE / NEAR-BULL CONTEXT"
else:
    mechanical_state = "WEAK / BELOW-200DMA"

regime = {
    "as_of":as_of,
    "spy_drawdown_from_ath":drawdown,
    "days_since_last_ath":days_since_peak,
    "spy_above_200dma":bool(spy.iloc[-1] >= ma200.iloc[-1]),
    "spy_return_21":cumret(spy,21),
    "spy_return_63":cumret(spy,63),
    "spy_return_126":cumret(spy,126),
    "spy_return_252":cumret(spy,252),
    "mechanical_state":mechanical_state,
    "warning":"Mechanical context only. Do not relabel style underperformance as a separate style bear market."
}
pd.DataFrame([regime]).to_csv(OUT/"market_regime_latest.csv", index=False)

# ---------- Bounce-effect context ----------
context_tickers = inst[inst["dashboard_default"].astype(str).str.upper().eq("TRUE")]["ticker"].tolist()
bounce_rows = []
for t in context_tickers:
    if t not in close.columns:
        continue
    bounce_rows.append({
        "as_of":as_of,
        "ticker":t,
        "group":inst.loc[inst["ticker"].eq(t),"group"].iloc[0],
        "subgroup":inst.loc[inst["ticker"].eq(t),"subgroup"].iloc[0],
        "max_drawdown_252":max_drawdown(close[t],252),
        "max_drawdown_126":max_drawdown(close[t],126),
        "rebound_from_126d_low":rebound_from_low(close[t],126),
        "current_drawdown_from_126d_high":float(close[t].iloc[-1] / close[t].tail(126).max() - 1)
    })
pd.DataFrame(bounce_rows).to_csv(OUT/"bounce_context_latest.csv", index=False)

print("Leadership, global context, regime and bounce files updated.")

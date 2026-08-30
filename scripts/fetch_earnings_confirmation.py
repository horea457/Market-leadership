from pathlib import Path
import json
import os
import time
import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "alphavantage"
OUT = ROOT / "data" / "processed"
RAW.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)

API_KEY = os.getenv("ALPHAVANTAGE_API_KEY", "").strip()
BASE_URL = "https://www.alphavantage.co/query"

SECTOR_TICKER = {
    "기술": "XLK",
    "금융": "XLF",
    "산업재": "XLI",
    "에너지": "XLE",
    "소재": "XLB",
    "경기소비재": "XLY",
    "필수소비재": "XLP",
    "헬스케어": "XLV",
    "유틸리티": "XLU",
    "부동산": "XLRE",
    "커뮤니케이션서비스": "XLC",
    "커뮤니케이션": "XLC",
}


def to_num(v):
    try:
        if v in [None, "", "None", "null", "-", "N/A"]:
            return np.nan
        return float(str(v).replace("%", ""))
    except Exception:
        return np.nan


def api_call(function, symbol):
    cache = RAW / f"{function}_{symbol}.json"
    if cache.exists() and (time.time() - cache.stat().st_mtime) < 6 * 86400:
        return json.loads(cache.read_text(encoding="utf-8"))
    r = requests.get(
        BASE_URL,
        params={"function": function, "symbol": symbol, "apikey": API_KEY},
        timeout=40,
        headers={"User-Agent": "market-leadership-dashboard/1.0"},
    )
    r.raise_for_status()
    data = r.json()
    if any(k in data for k in ["Note", "Information", "Error Message"]):
        raise RuntimeError(str(data))
    cache.write_text(json.dumps(data), encoding="utf-8")
    # Keep well below typical public API pacing limits.
    time.sleep(float(os.getenv("ALPHAVANTAGE_CALL_SLEEP", "0.8")))
    return data


def choose_sector_sample():
    """Use top-weight IVV name per sector to fit within a free API budget."""
    p = OUT / "stock_supply_company_detail.csv"
    if not p.exists():
        raise FileNotFoundError(
            "stock_supply_company_detail.csv is required. Run fetch_stock_supply.py first."
        )
    x = pd.read_csv(p)
    if "universe" in x.columns:
        x = x[x["universe"].eq("US")].copy()
    if x.empty:
        raise RuntimeError("US stock-supply detail is empty.")

    sector_col = "sector_ko" if "sector_ko" in x.columns else "Sector"
    weight_col = None
    for c in ["Weight (%)", "weight_pct", "weight"]:
        if c in x.columns:
            weight_col = c
            break
    if weight_col is None:
        x["_weight"] = 1.0
        weight_col = "_weight"
    x[weight_col] = pd.to_numeric(x[weight_col], errors="coerce")

    ticker_col = "ticker" if "ticker" in x.columns else "yahoo_ticker"
    name_col = "name" if "name" in x.columns else ticker_col
    x["_ticker"] = x[ticker_col].astype(str).str.replace("-", ".", regex=False)
    x = x[x[sector_col].astype(str).isin(SECTOR_TICKER)].copy()
    names_per_sector = max(1, int(os.getenv("EARNINGS_NAMES_PER_SECTOR", "1")))
    sample = (
        x.sort_values([sector_col, weight_col], ascending=[True, False])
        .groupby(sector_col, as_index=False, group_keys=False)
        .head(names_per_sector)
        .reset_index(drop=True)
    )
    return sample, sector_col, weight_col, name_col


def parse_earnings(data):
    q = pd.DataFrame(data.get("quarterlyEarnings", []))
    if q.empty:
        return {}
    for c in ["reportedEPS", "estimatedEPS", "surprise", "surprisePercentage"]:
        if c in q.columns:
            q[c] = q[c].map(to_num)
    if "reportedDate" in q.columns:
        q["reportedDate"] = pd.to_datetime(q["reportedDate"], errors="coerce")
        q = q.sort_values("reportedDate", ascending=False)
    q4 = q.head(4).copy()
    s = pd.to_numeric(q4.get("surprisePercentage"), errors="coerce")
    return {
        "earnings_surprise_4q_avg_pct": s.mean() if s is not None else np.nan,
        "positive_surprise_pct": (s > 0).mean() if s is not None and s.notna().any() else np.nan,
        "latest_surprise_pct": s.iloc[0] if s is not None and len(s) and pd.notna(s.iloc[0]) else np.nan,
        "n_surprise_quarters": int(s.notna().sum()) if s is not None else 0,
    }


def first_list(data, candidates):
    for k in candidates:
        v = data.get(k)
        if isinstance(v, list) and v:
            return v
    return []


def find_num(record, candidates):
    for k in candidates:
        if k in record:
            v = to_num(record.get(k))
            if pd.notna(v):
                return v
    return np.nan


def revision_ratio(cur, prev):
    if pd.isna(cur) or pd.isna(prev):
        return np.nan
    denom = max(abs(prev), 0.01)
    return float((cur - prev) / denom)


def parse_estimates(data):
    # Alpha Vantage has changed casing/key conventions over time.
    # This parser intentionally accepts the documented snake-case fields
    # as well as common camelCase variants.
    qlist = first_list(data, [
        "quarterlyEarningsEstimates", "quarterly_earnings_estimates",
        "quarterlyEstimates", "quarterly_estimates",
    ])
    alist = first_list(data, [
        "annualEarningsEstimates", "annual_earnings_estimates",
        "annualEstimates", "annual_estimates",
    ])
    rec = qlist[0] if qlist else (alist[0] if alist else {})
    if not rec:
        return {}

    eps_cur = find_num(rec, [
        "eps_estimate_average", "epsEstimateAverage", "estimatedEPS", "eps_estimate",
    ])
    eps_30 = find_num(rec, [
        "eps_estimate_average_30_days_ago", "epsEstimateAverage30DaysAgo",
        "eps_estimate_30_days_ago",
    ])
    eps_60 = find_num(rec, [
        "eps_estimate_average_60_days_ago", "epsEstimateAverage60DaysAgo",
        "eps_estimate_60_days_ago",
    ])
    rev_cur = find_num(rec, [
        "revenue_estimate_average", "revenueEstimateAverage", "revenue_estimate",
    ])
    rev_30 = find_num(rec, [
        "revenue_estimate_average_30_days_ago", "revenueEstimateAverage30DaysAgo",
        "revenue_estimate_30_days_ago",
    ])
    analyst_count = find_num(rec, ["eps_estimate_analyst_count", "analystCount", "analyst_count"])

    return {
        "eps_estimate": eps_cur,
        "eps_estimate_30d_ago": eps_30,
        "eps_estimate_60d_ago": eps_60,
        "eps_revision_30d": revision_ratio(eps_cur, eps_30),
        "eps_revision_60d": revision_ratio(eps_cur, eps_60),
        "revenue_estimate": rev_cur,
        "revenue_estimate_30d_ago": rev_30,
        "revenue_revision_30d": revision_ratio(rev_cur, rev_30),
        "analyst_count": analyst_count,
        "estimate_period": rec.get("fiscalDateEnding") or rec.get("horizon") or rec.get("date"),
    }


def main():
    if not API_KEY:
        print("ALPHAVANTAGE_API_KEY not set; earnings confirmation skipped. Existing files are preserved.")
        return

    sample, sector_col, weight_col, name_col = choose_sector_sample()
    rows = []

    for _, r in sample.iterrows():
        symbol = str(r["_ticker"]).upper()
        try:
            earnings = api_call("EARNINGS", symbol)
            estimates = api_call("EARNINGS_ESTIMATES", symbol)
        except Exception as exc:
            print("Alpha Vantage failed", symbol, exc)
            continue

        sector_ko = str(r[sector_col])
        row = {
            "as_of": pd.Timestamp.utcnow().date().isoformat(),
            "ticker": symbol,
            "company": r.get(name_col, symbol),
            "sector_ko": sector_ko,
            "sector_etf": SECTOR_TICKER.get(sector_ko),
            "sample_weight_pct": to_num(r.get(weight_col)),
            "source": "Alpha Vantage EARNINGS + EARNINGS_ESTIMATES",
        }
        row.update(parse_earnings(earnings))
        row.update(parse_estimates(estimates))
        rows.append(row)

    detail = pd.DataFrame(rows)
    if detail.empty:
        print("No earnings confirmation rows; existing outputs preserved.")
        return

    detail.to_csv(OUT / "sector_earnings_confirmation_company_detail.csv", index=False)

    # Top-weight sample per sector; default is one name to fit typical free API budgets.
    agg_rows = []
    for (sector_ko, etf), g in detail.groupby(["sector_ko", "sector_etf"], dropna=False):
        agg_rows.append({
            "as_of": detail["as_of"].max(),
            "ticker": etf,
            "sector_ko": sector_ko,
            "earnings_surprise_4q_avg_pct": pd.to_numeric(g["earnings_surprise_4q_avg_pct"], errors="coerce").median(),
            "positive_surprise_pct": pd.to_numeric(g["positive_surprise_pct"], errors="coerce").median(),
            "eps_revision_30d": pd.to_numeric(g["eps_revision_30d"], errors="coerce").median(),
            "eps_revision_60d": pd.to_numeric(g["eps_revision_60d"], errors="coerce").median(),
            "revenue_revision_30d": pd.to_numeric(g["revenue_revision_30d"], errors="coerce").median(),
            "n_sampled_names": len(g),
            "sampled_index_weight_pct": pd.to_numeric(g["sample_weight_pct"], errors="coerce").sum(min_count=1),
            "source": "Alpha Vantage; top-weight sector proxy unless sample widened",
        })

    out = pd.DataFrame(agg_rows)
    for c in ["eps_revision_30d", "earnings_surprise_4q_avg_pct", "positive_surprise_pct"]:
        out[f"rank_{c}"] = pd.to_numeric(out[c], errors="coerce").rank(ascending=False, method="min").astype("Int64")
    out.to_csv(OUT / "sector_earnings_confirmation_latest.csv", index=False)
    print(f"Earnings confirmation updated: sampled names={len(detail)}, sectors={len(out)}")


if __name__ == "__main__":
    main()

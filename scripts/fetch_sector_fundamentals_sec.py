from pathlib import Path
from io import StringIO
import json
import os
import time
import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "sec_companyfacts"
OUT = ROOT / "data" / "processed"
RAW.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)

CONSTITUENTS_URL = (
    "https://raw.githubusercontent.com/"
    "datasets/s-and-p-500-companies/refs/heads/main/data/constituents.csv"
)
COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
USER_AGENT = os.getenv(
    "SEC_USER_AGENT",
    "MarketLeadershipDashboard/1.0 github.com/horea457/Market-leadership",
)
HEADERS = {"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"}

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

CONCEPTS = {
    "assets": ["Assets"],
    "revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet",
        "Revenues",
    ],
    "net_income": ["NetIncomeLoss", "ProfitLoss"],
    "capex": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsToAcquireProductiveAssets",
        "PaymentsForAdditionsToPropertyPlantAndEquipment",
    ],
}


def get_json(url, timeout=40):
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.json()


def load_constituents():
    cache = ROOT / "data" / "raw" / "sp500_constituents.csv"
    if cache.exists():
        df = pd.read_csv(cache)
    else:
        r = requests.get(CONSTITUENTS_URL, timeout=30, headers={"User-Agent": USER_AGENT})
        r.raise_for_status()
        df = pd.read_csv(StringIO(r.text))
        cache.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(cache, index=False)
    if "yf_symbol" not in df.columns:
        df["yf_symbol"] = df["Symbol"].astype(str).str.replace(".", "-", regex=False)
    return df


def load_weights():
    """Prefer IVV-derived weights already produced by the stock-supply pipeline."""
    p = OUT / "stock_supply_company_detail.csv"
    if not p.exists():
        return pd.DataFrame()
    x = pd.read_csv(p)
    if "universe" in x.columns:
        x = x[x["universe"].eq("US")].copy()
    for c in ["Weight (%)", "weight_pct", "weight"]:
        if c in x.columns:
            x["_weight"] = pd.to_numeric(x[c], errors="coerce")
            break
    else:
        x["_weight"] = np.nan
    if "ticker" not in x.columns:
        return pd.DataFrame()
    x["ticker_norm"] = x["ticker"].astype(str).str.replace(".", "-", regex=False)
    return x


def ticker_cik_map():
    cache = ROOT / "data" / "raw" / "sec_company_tickers.json"
    if cache.exists() and (time.time() - cache.stat().st_mtime) < 7 * 86400:
        data = json.loads(cache.read_text(encoding="utf-8"))
    else:
        data = get_json(COMPANY_TICKERS_URL)
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(data), encoding="utf-8")
    out = {}
    for v in data.values():
        t = str(v.get("ticker", "")).replace(".", "-").upper()
        if t:
            out[t] = int(v["cik_str"])
    return out


def companyfacts(cik):
    p = RAW / f"CIK{int(cik):010d}.json"
    if p.exists() and (time.time() - p.stat().st_mtime) < 14 * 86400:
        return json.loads(p.read_text(encoding="utf-8"))
    data = get_json(COMPANYFACTS_URL.format(cik=int(cik)))
    p.write_text(json.dumps(data), encoding="utf-8")
    time.sleep(0.12)
    return data


def concept_units(cf, concepts):
    facts = cf.get("facts", {}).get("us-gaap", {})
    for concept in concepts:
        node = facts.get(concept)
        if not node:
            continue
        units = node.get("units", {})
        for unit in ["USD", "USD/shares", "shares", "pure"]:
            if unit in units and units[unit]:
                return units[unit], concept
        for unit, vals in units.items():
            if vals:
                return vals, concept
    return [], None


def annual_series(cf, concepts):
    vals, concept = concept_units(cf, concepts)
    if not vals:
        return pd.DataFrame(), concept
    rows = []
    for u in vals:
        form = str(u.get("form", ""))
        fp = str(u.get("fp", ""))
        fy = u.get("fy")
        start, end = u.get("start"), u.get("end")
        val = u.get("val")
        if form not in ["10-K", "10-K/A"]:
            continue
        if fy is None or val is None or end is None:
            continue
        # Prefer annual-duration facts. Instant facts (Assets) have no start.
        if start:
            try:
                days = (pd.Timestamp(end) - pd.Timestamp(start)).days
                if not (300 <= days <= 430):
                    continue
            except Exception:
                pass
        rows.append({
            "fy": int(fy), "val": float(val), "filed": u.get("filed"),
            "end": end, "fp": fp, "form": form,
        })
    if not rows:
        return pd.DataFrame(), concept
    x = pd.DataFrame(rows)
    x["filed_dt"] = pd.to_datetime(x["filed"], errors="coerce")
    # One observation per fiscal year: latest filing wins.
    x = x.sort_values(["fy", "filed_dt"]).groupby("fy", as_index=False).tail(1)
    return x.sort_values("fy"), concept


def latest_two(cf, concepts):
    x, concept = annual_series(cf, concepts)
    if len(x) < 1:
        return None, None, None, concept
    cur = x.iloc[-1]
    prev = x.iloc[-2] if len(x) >= 2 else None
    return (
        float(cur["val"]) if pd.notna(cur["val"]) else None,
        float(prev["val"]) if prev is not None and pd.notna(prev["val"]) else None,
        int(cur["fy"]),
        concept,
    )


def growth(cur, prev):
    if cur is None or prev is None or prev == 0:
        return np.nan
    return float(cur / prev - 1)


def select_sample(const, weights, top_n=5):
    x = const[["Symbol", "Security", "GICS Sector", "yf_symbol"]].copy()
    x["ticker_norm"] = x["yf_symbol"].str.upper()
    if not weights.empty:
        w = weights[["ticker_norm", "_weight"]].drop_duplicates("ticker_norm")
        x = x.merge(w, on="ticker_norm", how="left")
    else:
        x["_weight"] = np.nan
    # If weights are unavailable, alphabetical selection keeps the method deterministic.
    x["_sort_weight"] = x["_weight"].fillna(-1)
    return (
        x.sort_values(["GICS Sector", "_sort_weight", "ticker_norm"], ascending=[True, False, True])
        .groupby("GICS Sector", as_index=False, group_keys=False)
        .head(top_n)
        .reset_index(drop=True)
    )


def main():
    const = load_constituents()
    weights = load_weights()
    sample = select_sample(const, weights, top_n=int(os.getenv("SEC_NAMES_PER_SECTOR", "5")))
    cik_map = ticker_cik_map()

    rows = []
    for _, meta in sample.iterrows():
        ticker = str(meta["ticker_norm"]).upper()
        cik = cik_map.get(ticker)
        if cik is None:
            print("No CIK", ticker)
            continue
        try:
            cf = companyfacts(cik)
        except Exception as exc:
            print("SEC companyfacts failed", ticker, exc)
            continue

        a_cur, a_prev, fy, a_con = latest_two(cf, CONCEPTS["assets"])
        r_cur, r_prev, _, r_con = latest_two(cf, CONCEPTS["revenue"])
        n_cur, n_prev, _, n_con = latest_two(cf, CONCEPTS["net_income"])
        c_cur, c_prev, _, c_con = latest_two(cf, CONCEPTS["capex"])

        rows.append({
            "as_of": pd.Timestamp.utcnow().date().isoformat(),
            "ticker": ticker,
            "company": meta["Security"],
            "gics_sector": meta["GICS Sector"],
            "sector_ko": SECTOR_KO.get(meta["GICS Sector"], meta["GICS Sector"]),
            "sector_etf": SECTOR_ETF.get(meta["GICS Sector"]),
            "weight_pct": meta.get("_weight"),
            "cik": cik,
            "fiscal_year": fy,
            "assets": a_cur,
            "asset_growth_yoy": growth(a_cur, a_prev),
            "revenue": r_cur,
            "revenue_growth_yoy": growth(r_cur, r_prev),
            "net_income": n_cur,
            "profitable": (n_cur is not None and n_cur > 0),
            "capex": c_cur,
            "capex_growth_yoy": growth(c_cur, c_prev),
            "capex_intensity": (c_cur / r_cur) if c_cur is not None and r_cur not in [None, 0] else np.nan,
            "assets_concept": a_con,
            "revenue_concept": r_con,
            "net_income_concept": n_con,
            "capex_concept": c_con,
            "source": "SEC EDGAR Companyfacts",
        })

    detail = pd.DataFrame(rows)
    if detail.empty:
        print("No SEC fundamental rows; leaving existing outputs untouched.")
        return

    detail.to_csv(OUT / "sector_fundamentals_company_detail.csv", index=False)

    aggs = []
    for (gics, etf), g in detail.groupby(["gics_sector", "sector_etf"], dropna=False):
        sampled_weight = pd.to_numeric(g["weight_pct"], errors="coerce").sum(min_count=1)
        aggs.append({
            "as_of": detail["as_of"].max(),
            "ticker": etf,
            "gics_sector": gics,
            "sector_ko": SECTOR_KO.get(gics, gics),
            "median_asset_growth_yoy": pd.to_numeric(g["asset_growth_yoy"], errors="coerce").median(),
            "median_revenue_growth_yoy": pd.to_numeric(g["revenue_growth_yoy"], errors="coerce").median(),
            "median_capex_growth_yoy": pd.to_numeric(g["capex_growth_yoy"], errors="coerce").median(),
            "median_capex_intensity": pd.to_numeric(g["capex_intensity"], errors="coerce").median(),
            "profitable_share": pd.to_numeric(g["profitable"], errors="coerce").mean(),
            "n_companies": len(g),
            "n_asset_growth": pd.to_numeric(g["asset_growth_yoy"], errors="coerce").notna().sum(),
            "n_capex_growth": pd.to_numeric(g["capex_growth_yoy"], errors="coerce").notna().sum(),
            "sampled_index_weight_pct": sampled_weight,
            "source": "SEC EDGAR Companyfacts; current S&P 500 top-weight sample",
        })

    sec = pd.DataFrame(aggs)
    for c in ["median_asset_growth_yoy", "median_capex_growth_yoy", "median_revenue_growth_yoy"]:
        sec[f"rank_{c}"] = pd.to_numeric(sec[c], errors="coerce").rank(ascending=False, method="min").astype("Int64")
        sec[f"pct_{c}"] = pd.to_numeric(sec[c], errors="coerce").rank(pct=True, ascending=True)

    sec.to_csv(OUT / "sector_fundamentals_latest.csv", index=False)
    print(f"SEC sector fundamentals updated: companies={len(detail)}, sectors={len(sec)}")


if __name__ == "__main__":
    main()

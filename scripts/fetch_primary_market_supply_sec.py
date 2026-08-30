from pathlib import Path
import gzip
import json
import os
import re
import time
from datetime import date
import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "sec_full_index"
CF_CACHE = ROOT / "data" / "raw" / "sec_companyfacts"
OUT = ROOT / "data" / "processed"
RAW.mkdir(parents=True, exist_ok=True)
CF_CACHE.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)

USER_AGENT = os.getenv(
    "SEC_USER_AGENT",
    "MarketLeadershipDashboard/1.0 github.com/horea457/Market-leadership",
)
HEADERS = {"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"}
MASTER_URL = "https://www.sec.gov/Archives/edgar/full-index/{year}/QTR{quarter}/master.gz"
COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"

FORMS = {"424B4", "424B5", "S-1", "S-1/A"}
SPAC_RE = re.compile(r"\b(acquisition|blank\s+check|spac|acquisition\s+corp|acquisition\s+company)\b", re.I)


def quarter_of_month(month):
    return (month - 1) // 3 + 1


def quarter_range(years_back=5):
    now = pd.Timestamp.utcnow().tz_localize(None)
    current = (now.year, quarter_of_month(now.month))
    pairs = []
    y, q = current
    for _ in range(years_back * 4):
        pairs.append((y, q))
        q -= 1
        if q == 0:
            y -= 1
            q = 4
    return sorted(pairs)


def download_master(year, q):
    p = RAW / f"master_{year}_QTR{q}.gz"
    current_q = (year == pd.Timestamp.utcnow().year and q == quarter_of_month(pd.Timestamp.utcnow().month))
    max_age = 2 * 86400 if current_q else 60 * 86400
    if p.exists() and (time.time() - p.stat().st_mtime) < max_age:
        raw = p.read_bytes()
    else:
        url = MASTER_URL.format(year=year, quarter=q)
        r = requests.get(url, headers=HEADERS, timeout=60)
        if r.status_code == 404:
            return pd.DataFrame()
        r.raise_for_status()
        raw = r.content
        p.write_bytes(raw)
        time.sleep(0.15)
    try:
        txt = gzip.decompress(raw).decode("latin-1", errors="ignore")
    except Exception:
        txt = raw.decode("latin-1", errors="ignore")

    rows = []
    for line in txt.splitlines():
        parts = line.strip().split("|")
        if len(parts) != 5:
            continue
        cik, name, form, filed, filename = parts
        if not cik.isdigit() or form not in FORMS:
            continue
        rows.append({
            "cik": int(cik),
            "company": name.strip(),
            "form": form.strip(),
            "filed": filed.strip(),
            "filename": filename.strip(),
        })
    return pd.DataFrame(rows)


def companyfacts(cik):
    p = CF_CACHE / f"CIK{int(cik):010d}.json"
    if p.exists() and (time.time() - p.stat().st_mtime) < 14 * 86400:
        return json.loads(p.read_text(encoding="utf-8"))
    r = requests.get(COMPANYFACTS_URL.format(cik=int(cik)), headers=HEADERS, timeout=40)
    if r.status_code != 200:
        return None
    data = r.json()
    p.write_text(json.dumps(data), encoding="utf-8")
    time.sleep(0.12)
    return data


def annual_latest(cf, concepts):
    if not cf:
        return np.nan
    facts = cf.get("facts", {}).get("us-gaap", {})
    for concept in concepts:
        node = facts.get(concept)
        if not node:
            continue
        units = node.get("units", {})
        vals = units.get("USD", [])
        rows = []
        for u in vals:
            if str(u.get("form", "")) not in ["10-K", "10-K/A"]:
                continue
            val = u.get("val")
            fy = u.get("fy")
            if val is None or fy is None:
                continue
            start, end = u.get("start"), u.get("end")
            if start and end:
                try:
                    days = (pd.Timestamp(end) - pd.Timestamp(start)).days
                    if not (300 <= days <= 430):
                        continue
                except Exception:
                    pass
            rows.append((int(fy), str(u.get("filed", "")), float(val)))
        if rows:
            rows.sort()
            return rows[-1][2]
    return np.nan


def pct_rank_last(series):
    x = pd.to_numeric(series, errors="coerce").dropna()
    if len(x) < 6:
        return np.nan
    return float(x.rank(pct=True, method="average").iloc[-1])


def main():
    frames = []
    for y, q in quarter_range(int(os.getenv("SEC_SUPPLY_YEARS", "5"))):
        try:
            d = download_master(y, q)
            if len(d):
                frames.append(d)
        except Exception as exc:
            print("SEC full-index failed", y, q, exc)

    if not frames:
        print("No SEC master-index data; existing outputs preserved.")
        return

    filings = pd.concat(frames, ignore_index=True)
    filings["filed"] = pd.to_datetime(filings["filed"], errors="coerce")
    filings = filings.dropna(subset=["filed"]).drop_duplicates(["cik", "form", "filed", "filename"])
    filings["month"] = filings["filed"].dt.to_period("M").dt.to_timestamp("M")

    counts = (
        filings.groupby(["month", "form"]).size().unstack(fill_value=0).sort_index()
    )
    for form in FORMS:
        if form not in counts.columns:
            counts[form] = 0

    full_months = pd.date_range(counts.index.min(), counts.index.max(), freq="ME")
    counts = counts.reindex(full_months, fill_value=0)
    counts.index.name = "month"

    hist = counts.reset_index().copy()
    hist["ipo_proxy_count"] = hist["424B4"]
    hist["followon_proxy_count"] = hist["424B5"]
    hist["registration_count"] = hist["S-1"] + hist["S-1/A"]
    for c in ["ipo_proxy_count", "followon_proxy_count", "registration_count"]:
        hist[f"{c}_3m"] = hist[c].rolling(3, min_periods=1).sum()

    # Expanding.rank isn't available in every pandas build; compute safely.
    for c in ["ipo_proxy_count", "followon_proxy_count", "registration_count"]:
        rollcol = f"{c}_3m"
        vals = hist[rollcol].tolist()
        pctiles = []
        for i, v in enumerate(vals):
            prior = pd.Series(vals[:i+1], dtype=float).dropna()
            pctiles.append(float((prior <= v).mean()) if len(prior) >= 12 else np.nan)
        hist[f"{c}_pctile"] = pctiles

    hist["supply_percentile"] = hist[[
        "ipo_proxy_count_pctile", "followon_proxy_count_pctile", "registration_count_pctile"
    ]].mean(axis=1, skipna=True)

    def supply_state(p):
        if pd.isna(p):
            return "normal"
        if p >= 0.90:
            return "frenzy"
        if p >= 0.70:
            return "rising"
        if p <= 0.30:
            return "subdued"
        return "normal"

    hist["supply_state"] = hist["supply_percentile"].map(supply_state)
    hist["source"] = "SEC EDGAR full-index; 424B4/424B5/S-1 filing-count proxies"
    hist.to_csv(OUT / "primary_market_supply_history.csv", index=False)

    # Low-quality issuance proxy among recent 424B4 issuers.
    cutoff = filings["filed"].max() - pd.Timedelta(days=90)
    recent = filings[(filings["filed"] >= cutoff) & filings["form"].eq("424B4")].copy()
    recent = recent.sort_values("filed", ascending=False).drop_duplicates("cik")
    max_names = int(os.getenv("SEC_LOW_QUALITY_SAMPLE", "50"))
    recent = recent.head(max_names)

    quality_rows = []
    for _, rr in recent.iterrows():
        spac_like = bool(SPAC_RE.search(str(rr["company"])))
        ni = np.nan
        rev = np.nan
        cf_ok = False
        try:
            cf = companyfacts(int(rr["cik"]))
            if cf:
                ni = annual_latest(cf, ["NetIncomeLoss", "ProfitLoss"])
                rev = annual_latest(cf, [
                    "RevenueFromContractWithCustomerExcludingAssessedTax",
                    "SalesRevenueNet", "Revenues",
                ])
                cf_ok = True
        except Exception as exc:
            print("Recent issuer companyfacts failed", rr["cik"], exc)

        loss_making = pd.notna(ni) and ni <= 0
        pre_revenue = pd.notna(rev) and rev <= 0
        low_quality = spac_like or loss_making or pre_revenue
        quality_rows.append({
            "cik": rr["cik"], "company": rr["company"], "filed": rr["filed"],
            "spac_like": spac_like, "net_income": ni, "revenue": rev,
            "loss_making": loss_making, "pre_revenue": pre_revenue,
            "low_quality_proxy": low_quality, "companyfacts_available": cf_ok,
        })

    qdf = pd.DataFrame(quality_rows)
    if len(qdf):
        quality_share = float(qdf["low_quality_proxy"].mean())
        quality_coverage = float(qdf["companyfacts_available"].mean())
        qdf.to_csv(OUT / "primary_market_supply_recent_issuers.csv", index=False)
    else:
        quality_share = np.nan
        quality_coverage = np.nan

    if pd.isna(quality_share):
        low_state = "unknown"
    elif quality_share >= 0.60:
        low_state = "high"
    elif quality_share >= 0.35:
        low_state = "normal"
    else:
        low_state = "low"

    last = hist.iloc[-1]
    latest = pd.DataFrame([{
        "as_of": filings["filed"].max().date().isoformat(),
        "supply_state": last["supply_state"],
        "supply_percentile": last["supply_percentile"],
        "ipo_proxy_count_3m": last["ipo_proxy_count_3m"],
        "followon_proxy_count_3m": last["followon_proxy_count_3m"],
        "registration_count_3m": last["registration_count_3m"],
        "low_quality_state": low_state,
        "low_quality_share": quality_share,
        "low_quality_sample_n": len(qdf),
        "companyfacts_coverage": quality_coverage,
        "definition": "SEC filing proxy: 424B4 / 424B5 / S-1; low quality = SPAC-like or loss/pre-revenue among sampled recent 424B4 issuers",
        "caveat": "Filing counts are issuance proxies, not a transaction-perfect IPO/SEO database.",
        "source": "SEC EDGAR full-index + Companyfacts",
    }])
    latest.to_csv(OUT / "primary_market_supply_latest.csv", index=False)
    print(
        "Primary-market supply updated:",
        latest[["supply_state", "supply_percentile", "low_quality_state", "low_quality_share"]].to_dict("records")[0]
    )


if __name__ == "__main__":
    main()

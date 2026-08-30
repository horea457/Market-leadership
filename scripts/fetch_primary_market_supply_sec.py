
from pathlib import Path
from datetime import date
import os, re, time
import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"
OUT.mkdir(parents=True, exist_ok=True)
RAW.mkdir(parents=True, exist_ok=True)

# IMPORTANT:
# GitHub Actions turns a missing secret into an empty string.
# `os.environ.get("SEC_USER_AGENT", fallback)` does NOT use fallback in that case.
# Therefore use `or fallback`.
repo_name = os.environ.get("GITHUB_REPOSITORY", "market-leadership-dashboard")
SEC_UA = (
    (os.environ.get("SEC_USER_AGENT") or "").strip()
    or f"MarketLeadershipDashboard/1.0 contact:https://github.com/{repo_name}"
)

SEC_HEADERS = {
    "User-Agent": SEC_UA,
    "Accept-Encoding": "gzip, deflate",
    "Accept": "text/plain,text/html,application/json;q=0.9,*/*;q=0.8",
}
DATA_HEADERS = {
    "User-Agent": SEC_UA,
    "Accept-Encoding": "gzip, deflate",
    "Accept": "application/json,text/plain,*/*",
}

CACHE = RAW / "sec_issuer_quality_cache.csv"
FILINGS_CACHE = RAW / "sec_primary_supply_filings_cache.csv"
LATEST_FILE = OUT / "primary_market_supply_latest.csv"
HISTORY_FILE = OUT / "primary_market_supply_history.csv"
QUALITY_FILE = OUT / "primary_market_supply_recent_issuer_quality.csv"

FORMS = {"424B4", "424B5", "S-1", "S-1/A"}
SPAC_RE = re.compile(r"\b(acquisition|blank check)\b", re.I)

session = requests.Session()
session.headers.update(SEC_HEADERS)


def quarter(d):
    return (d.month - 1) // 3 + 1


def sec_get(url, *, json_mode=False, attempts=4):
    """
    Fair-access SEC request:
    - explicit non-empty user agent
    - < 10 req/s
    - exponential backoff for 403/429/5xx
    """
    headers = DATA_HEADERS if "data.sec.gov" in url else SEC_HEADERS
    last_exc = None

    for attempt in range(attempts):
        try:
            r = session.get(url, headers=headers, timeout=45)

            if r.status_code == 200:
                time.sleep(0.18)  # comfortably below SEC's 10 req/sec ceiling
                return r.json() if json_mode else r.text

            if r.status_code in {403, 429, 500, 502, 503, 504}:
                wait = min(2 ** attempt * 2, 20)
                print(
                    f"WARN SEC {r.status_code}: {url} "
                    f"(attempt {attempt + 1}/{attempts}, wait {wait}s)"
                )
                time.sleep(wait)
                continue

            r.raise_for_status()

        except Exception as exc:
            last_exc = exc
            wait = min(2 ** attempt * 2, 20)
            print(
                f"WARN SEC request error: {url}: {exc} "
                f"(attempt {attempt + 1}/{attempts}, wait {wait}s)"
            )
            time.sleep(wait)

    if last_exc:
        raise RuntimeError(f"SEC request failed after retries: {url}: {last_exc}")
    raise RuntimeError(f"SEC request failed after retries: {url}")


def parse_master(text):
    lines = text.splitlines()
    start = 0

    for i, line in enumerate(lines):
        if line.startswith("CIK|Company Name|Form Type|Date Filed|Filename"):
            start = i + 1
            break

    rows = []
    for line in lines[start:]:
        p = line.split("|")
        if len(p) != 5:
            continue
        cik, name, form, dt, fn = p
        form = form.strip()
        if form not in FORMS:
            continue
        rows.append(
            {
                "cik": str(cik).strip(),
                "company_name": name.strip(),
                "form": form,
                "date": pd.to_datetime(dt, errors="coerce"),
                "filename": fn.strip(),
            }
        )
    return pd.DataFrame(rows)


def load_existing_filings_cache():
    if not FILINGS_CACHE.exists():
        return pd.DataFrame(
            columns=["cik", "company_name", "form", "date", "filename"]
        )
    x = pd.read_csv(FILINGS_CACHE, dtype={"cik": str})
    if "date" in x.columns:
        x["date"] = pd.to_datetime(x["date"], errors="coerce")
    return x


def load_history(years=5):
    """
    Use SEC's official EDGAR quarterly full-index files.
    Historical quarters already cached locally are not downloaded again.
    """
    today = date.today()
    start_year = today.year - years
    cache = load_existing_filings_cache()

    pieces = [cache] if len(cache) else []
    cached_q = set()

    if len(cache) and "date" in cache.columns:
        tmp = cache.dropna(subset=["date"]).copy()
        for d in tmp["date"]:
            cached_q.add((d.year, quarter(d.date())))

    successful_fetches = 0

    for y in range(start_year, today.year + 1):
        qmax = quarter(today) if y == today.year else 4

        for q in range(1, qmax + 1):
            # Always refresh the current quarter; historical quarters can use cache.
            is_current_q = y == today.year and q == quarter(today)
            if (y, q) in cached_q and not is_current_q:
                continue

            url = (
                f"https://www.sec.gov/Archives/edgar/full-index/"
                f"{y}/QTR{q}/master.idx"
            )
            try:
                txt = sec_get(url)
                part = parse_master(txt)
                if len(part):
                    pieces.append(part)
                successful_fetches += 1
            except Exception as exc:
                print(f"WARN index {y} Q{q}: {exc}")

    if not pieces:
        raise RuntimeError(
            "SEC index unavailable and no local SEC filings cache exists."
        )

    x = pd.concat(pieces, ignore_index=True)
    if x.empty:
        raise RuntimeError("SEC filing cache contains no usable rows.")

    x["date"] = pd.to_datetime(x["date"], errors="coerce")
    x = x[x["date"].notna()].copy()
    x = x[x["date"].dt.date <= today]
    x = x.drop_duplicates(
        subset=["cik", "form", "date", "filename"], keep="last"
    ).sort_values("date")

    # Keep a durable cache so SEC downtime does not break future runs.
    cache_write = x.copy()
    cache_write["date"] = cache_write["date"].dt.strftime("%Y-%m-%d")
    cache_write.to_csv(FILINGS_CACHE, index=False)

    print(
        f"SEC filing history rows={len(x):,}; "
        f"successful network index fetches={successful_fetches}"
    )
    return x


def latest_profitability(cik):
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{int(cik):010d}.json"
    try:
        data = sec_get(url, json_mode=True, attempts=3)
    except Exception:
        return None

    facts = data.get("facts", {})
    candidates = []

    for taxonomy, concept in [
        ("us-gaap", "NetIncomeLoss"),
        ("ifrs-full", "ProfitLoss"),
        ("ifrs-full", "ProfitLossAttributableToOwnersOfParent"),
    ]:
        units = facts.get(taxonomy, {}).get(concept, {}).get("units", {})
        for unit, arr in units.items():
            if unit not in {"USD", "EUR", "GBP", "JPY", "CNY", "CAD", "CHF", "KRW"}:
                continue

            for r in arr:
                fp = str(r.get("fp", ""))
                form = str(r.get("form", ""))
                val = r.get("val")
                filed = r.get("filed")
                if val is None or not filed:
                    continue
                if form in {"10-K", "20-F", "40-F"} or fp == "FY":
                    try:
                        candidates.append((filed, float(val)))
                    except Exception:
                        pass

    if not candidates:
        return None

    candidates.sort(key=lambda z: z[0])
    return candidates[-1][1] > 0


def issuer_quality(recent):
    if CACHE.exists():
        cache = pd.read_csv(CACHE, dtype={"cik": str})
    else:
        cache = pd.DataFrame(columns=["cik", "profitable", "checked_at"])

    known = {str(r["cik"]): r for _, r in cache.iterrows()}
    out = []

    # Cap first-run SEC calls to avoid triggering fair-access protection.
    candidates = recent.drop_duplicates("cik").head(35)

    for _, r in candidates.iterrows():
        cik = str(r["cik"])
        name = str(r["company_name"])
        spac = bool(SPAC_RE.search(name))
        prof = None

        if cik in known and pd.notna(known[cik].get("profitable")):
            raw = known[cik].get("profitable")
            prof = str(raw).lower() in {"true", "1", "yes"}
        elif not spac:
            prof = latest_profitability(cik)

        low_quality = True if spac else (None if prof is None else not prof)
        out.append(
            {
                "cik": cik,
                "company_name": name,
                "spac": spac,
                "profitable": prof,
                "low_quality": low_quality,
            }
        )

    fresh = pd.DataFrame(out)

    if len(fresh):
        cache_new = fresh[["cik", "profitable"]].copy()
        cache_new["checked_at"] = date.today().isoformat()
        cache_all = pd.concat([cache, cache_new], ignore_index=True)
        cache_all = cache_all.drop_duplicates("cik", keep="last")
        cache_all.to_csv(CACHE, index=False)

    return fresh


def write_unavailable_status(reason):
    """
    SEC should never make the entire market dashboard fail.
    Preserve last good data if it exists; otherwise create a transparent
    'collection unavailable' status row.
    """
    if LATEST_FILE.exists():
        print(
            "WARNING: SEC primary supply refresh unavailable. "
            "Keeping previous primary_market_supply_latest.csv."
        )
        print("Reason:", reason)
        return

    row = {
        "as_of": date.today().isoformat(),
        "ready": False,
        "supply_state": "collection_unavailable",
        "low_quality_state": "unknown",
        "ipo_proxy_424b4_3m": np.nan,
        "followon_proxy_424b5_3m": np.nan,
        "s1_registration_3m": np.nan,
        "spac_proxy_3m": np.nan,
        "supply_percentile_5y": np.nan,
        "low_quality_share": np.nan,
        "low_quality_coverage": 0.0,
        "method_note": (
            "SEC EDGAR refresh unavailable on this run. "
            "Dashboard must treat this module as not connected."
        ),
        "data_source": "SEC EDGAR",
        "error_note": str(reason)[:500],
    }
    pd.DataFrame([row]).to_csv(LATEST_FILE, index=False)
    print("Wrote transparent unavailable-status row instead of failing workflow.")


def main():
    print("SEC User-Agent:", SEC_UA)

    try:
        filings = load_history(5)
    except Exception as exc:
        write_unavailable_status(exc)
        return  # fail-soft: do not kill the full GitHub Actions workflow

    filings["month"] = filings["date"].dt.to_period("M").astype(str)
    filings["spac_proxy"] = (
        filings["company_name"].str.contains(SPAC_RE, regex=True, na=False)
        & filings["form"].eq("424B4")
    )

    hist = (
        filings.groupby("month")
        .agg(
            count_424b4=("form", lambda s: int((s == "424B4").sum())),
            count_424b5=("form", lambda s: int((s == "424B5").sum())),
            count_s1=("form", lambda s: int(s.isin(["S-1", "S-1/A"]).sum())),
            count_spac_proxy=("spac_proxy", "sum"),
            unique_issuers=("cik", "nunique"),
        )
        .reset_index()
        .sort_values("month")
    )

    hist["primary_supply_events"] = (
        hist["count_424b4"] + hist["count_424b5"]
    )
    hist["supply_3m_avg"] = (
        hist["primary_supply_events"].rolling(3, min_periods=1).mean()
    )

    latest_3m = float(hist["supply_3m_avg"].iloc[-1])
    dist = hist["supply_3m_avg"].dropna()
    percentile = float((dist <= latest_3m).mean()) if len(dist) else np.nan

    if percentile >= 0.95:
        supply_state = "frenzy"
    elif percentile >= 0.80:
        supply_state = "rising"
    elif percentile <= 0.20:
        supply_state = "subdued"
    else:
        supply_state = "normal"

    cutoff = pd.Timestamp.today().normalize() - pd.Timedelta(days=92)
    recent = filings[
        (filings["date"] >= cutoff) & filings["form"].eq("424B4")
    ].copy()

    quality = issuer_quality(recent)

    if len(quality):
        covered = quality["low_quality"].notna()
        coverage = float(covered.mean())
        low_share = (
            float(quality.loc[covered, "low_quality"].astype(bool).mean())
            if covered.any()
            else np.nan
        )
    else:
        coverage = 0.0
        low_share = np.nan

    if coverage < 0.40 or pd.isna(low_share):
        lq_state = "unknown"
    elif low_share >= 0.50:
        lq_state = "high"
    elif low_share <= 0.25:
        lq_state = "low"
    else:
        lq_state = "normal"

    last3 = hist.tail(3)

    row = {
        "as_of": str(filings["date"].max().date()),
        "ready": True,
        "supply_state": supply_state,
        "low_quality_state": lq_state,
        "ipo_proxy_424b4_3m": int(last3["count_424b4"].sum()),
        "followon_proxy_424b5_3m": int(last3["count_424b5"].sum()),
        "s1_registration_3m": int(last3["count_s1"].sum()),
        "spac_proxy_3m": int(last3["count_spac_proxy"].sum()),
        "supply_percentile_5y": percentile,
        "low_quality_share": low_share,
        "low_quality_coverage": coverage,
        "method_note": (
            "SEC EDGAR proxy: 424B4 public-offering prospectus; "
            "424B5 shelf/follow-on prospectus; S-1 registrations. "
            "SPAC proxy uses acquisition/blank-check issuer names. "
            "Low-quality proxy = SPAC or latest annual net loss where "
            "SEC XBRL coverage exists."
        ),
        "data_source": "SEC EDGAR full index + Companyfacts",
    }

    hist.to_csv(HISTORY_FILE, index=False)
    pd.DataFrame([row]).to_csv(LATEST_FILE, index=False)
    quality.to_csv(QUALITY_FILE, index=False)

    print(pd.DataFrame([row]).to_string(index=False))


if __name__ == "__main__":
    main()

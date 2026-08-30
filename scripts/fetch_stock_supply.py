from __future__ import annotations

from io import StringIO
from pathlib import Path
import math
import time
import warnings

import numpy as np
import pandas as pd
import requests
import yfinance as yf

warnings.filterwarnings("ignore", category=FutureWarning)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
RAW.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)

# Public iShares holdings files. They provide sector/country/weight metadata;
# issuer shares outstanding are fetched separately from Yahoo Finance.
HOLDINGS_URLS = {
    "US": [
        "https://www.ishares.com/us/products/239726/ishares-core-sp-500-etf/latest-holdings.csv",
        "https://www.ishares.com/us/products/239726/ishares-core-sp-500-etf/1467271812596.ajax?fileType=csv&fileName=IVV_holdings&dataType=fund",
    ],
    "GLOBAL": [
        "https://www.ishares.com/us/products/239600/ishares-msci-acwi-etf/latest-holdings.csv",
        "https://www.ishares.com/us/products/239600/ishares-msci-acwi-etf/1467271812596.ajax?fileType=csv&fileName=ACWI_holdings&dataType=fund",
    ],
}

# We intentionally sample each sector rather than hammering thousands of Yahoo endpoints.
# The dashboard exposes coverage, so the user can see how much of each ETF sector is represented.
MAX_NAMES_PER_SECTOR = {
    # Keep the initial weekly job light enough for GitHub Actions/Yahoo limits.
    # Weighted metrics still cover the largest names; breadth is a sampled proxy.
    "US": 12,
    "GLOBAL": 10,
    "EX_US": 8,
}
LOOKBACK_DAYS = 460
CHANGE_HORIZONS = {"3m": 91, "6m": 182, "12m": 365}
ISSUANCE_THRESHOLD = 0.01  # > +1% = meaningful issuance; < -1% = meaningful shrinkage
MIN_REFRESH_DAYS = 13

SECTOR_KOR = {
    "Information Technology": "기술",
    "Financials": "금융",
    "Industrials": "산업재",
    "Consumer Discretionary": "경기소비재",
    "Health Care": "헬스케어",
    "Communication": "커뮤니케이션",
    "Communication Services": "커뮤니케이션",
    "Consumer Staples": "필수소비재",
    "Energy": "에너지",
    "Materials": "소재",
    "Utilities": "유틸리티",
    "Real Estate": "부동산",
}


def _parse_ishares_text(text: str) -> pd.DataFrame:
    lines = text.splitlines()
    header_idx = None
    for i, line in enumerate(lines[:40]):
        clean = line.replace('"', '').strip()
        if clean.startswith("Ticker,Name,Sector,Asset Class"):
            header_idx = i
            break
    if header_idx is None:
        raise RuntimeError("Could not locate iShares holdings CSV header.")

    df = pd.read_csv(StringIO("\n".join(lines[header_idx:])))
    required = {"Ticker", "Name", "Sector", "Asset Class", "Weight (%)"}
    missing = required - set(df.columns)
    if missing:
        raise RuntimeError(f"iShares CSV missing columns: {sorted(missing)}")

    for col in ["Weight (%)", "Market Value", "Quantity", "Price"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", "", regex=False), errors="coerce")

    df = df[df["Asset Class"].astype(str).str.contains("Equity", case=False, na=False)].copy()
    df = df[df["Ticker"].notna() & df["Sector"].notna()].copy()
    for col in ["Ticker", "Sector", "Location", "Exchange", "ISIN", "Name"]:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].astype(str).str.strip()
    if df.empty:
        raise RuntimeError("Parsed iShares holdings but no equity rows remained.")
    return df


def _read_ishares_csv(urls: list[str], cache_path: Path, label: str) -> pd.DataFrame:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131 Safari/537.36",
        "Accept": "text/csv,text/plain,*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.ishares.com/us/",
    }
    errors = []
    session = requests.Session()
    for url in urls:
        for attempt in range(3):
            try:
                r = session.get(url, headers=headers, timeout=60, allow_redirects=True)
                ctype = (r.headers.get("content-type") or "").lower()
                preview = r.text[:80].replace("\n", " | ")
                print(f"  {label} holdings attempt {attempt+1}: HTTP {r.status_code}, {len(r.content)} bytes, {ctype}")
                r.raise_for_status()
                df = _parse_ishares_text(r.text)
                print(f"  {label} holdings OK: {len(df)} equity rows")
                df.to_csv(cache_path, index=False)
                return df
            except Exception as exc:
                errors.append(f"{url} -> {type(exc).__name__}: {exc}")
                time.sleep(1.5 * (attempt + 1))

    # A transient iShares block should not erase a previously usable universe.
    if cache_path.exists():
        try:
            cached = pd.read_csv(cache_path)
            if not cached.empty:
                print(f"WARNING: live {label} holdings failed; using cached {cache_path.name} ({len(cached)} rows).")
                return cached
        except Exception as exc:
            errors.append(f"cache -> {type(exc).__name__}: {exc}")

    raise RuntimeError(f"Unable to load {label} holdings. " + " || ".join(errors[-6:]))


def _normalize_us_ticker(ticker: str) -> str:
    # iShares often removes punctuation from US class-share tickers.
    special = {
        "BRKB": "BRK-B",
        "BRKA": "BRK-A",
        "BFB": "BF-B",
        "BFA": "BF-A",
    }
    return special.get(ticker, ticker.replace("/", "-"))


def _exchange_suffix(exchange: str, location: str) -> str | None:
    e = (exchange or "").lower()
    l = (location or "").lower()

    # NASDAQ is also part of some non-US exchange names, so country takes priority.
    if l == "united states":
        return ""

    rules = [
        (("taiwan stock exchange",), ".TW"),
        (("taipei exchange",), ".TWO"),
        (("kosdaq",), ".KQ"),
        (("korea exchange (stock market)", "korea exchange"), ".KS"),
        (("tokyo stock exchange", "japan exchange"), ".T"),
        (("hong kong",), ".HK"),
        (("london stock exchange",), ".L"),
        (("toronto stock exchange",), ".TO"),
        (("six swiss",), ".SW"),
        (("xetra", "frankfurt"), ".DE"),
        (("euronext amsterdam",), ".AS"),
        (("euronext paris",), ".PA"),
        (("euronext brussels",), ".BR"),
        (("euronext lisbon",), ".LS"),
        (("borsa italiana", "milan"), ".MI"),
        (("bolsa de madrid", "madrid"), ".MC"),
        (("australian securities exchange",), ".AX"),
        (("new zealand exchange",), ".NZ"),
        (("singapore exchange",), ".SI"),
        (("stockholm",), ".ST"),
        (("copenhagen",), ".CO"),
        (("helsinki",), ".HE"),
        (("oslo",), ".OL"),
        (("vienna",), ".VI"),
        (("warsaw",), ".WA"),
        (("tel aviv",), ".TA"),
        (("johannesburg",), ".JO"),
        (("mexican", "mexico"), ".MX"),
        (("b3", "sao paulo", "brazil"), ".SA"),
        (("indonesia",), ".JK"),
        (("bursa malaysia", "malaysia"), ".KL"),
        (("stock exchange of thailand", "thailand"), ".BK"),
        (("philippine",), ".PS"),
        (("national stock exchange of india", "nse"), ".NS"),
        (("bombay stock exchange", "bse"), ".BO"),
        (("shanghai",), ".SS"),
        (("shenzhen",), ".SZ"),
    ]
    for needles, suffix in rules:
        if any(n in e for n in needles):
            return suffix

    # Country fallbacks when exchange labels vary slightly.
    country_fallback = {
        "united states": "",
        "japan": ".T",
        "taiwan": ".TW",
        "korea (south)": ".KS",
        "hong kong": ".HK",
        "united kingdom": ".L",
        "canada": ".TO",
        "switzerland": ".SW",
        "germany": ".DE",
        "netherlands": ".AS",
        "france": ".PA",
        "italy": ".MI",
        "spain": ".MC",
        "australia": ".AX",
        "singapore": ".SI",
        "sweden": ".ST",
        "denmark": ".CO",
        "finland": ".HE",
        "norway": ".OL",
        "mexico": ".MX",
        "brazil": ".SA",
        "india": ".NS",
        "china": None,  # Shanghai/Shenzhen/HK cannot be inferred safely from country alone.
    }
    return country_fallback.get(l)


def to_yahoo_ticker(row: pd.Series) -> str | None:
    ticker = str(row.get("Ticker", "")).strip()
    if not ticker or ticker in {"-", "nan", "None"}:
        return None

    location = str(row.get("Location", ""))
    exchange = str(row.get("Exchange", ""))
    suffix = _exchange_suffix(exchange, location)

    if suffix == "":
        return _normalize_us_ticker(ticker)
    if suffix is None:
        return None

    if suffix == ".HK" and ticker.isdigit():
        ticker = ticker.zfill(4)
    if suffix in {".KS", ".KQ"} and ticker.isdigit():
        ticker = ticker.zfill(6)
    return f"{ticker}{suffix}"


def _sample_holdings(df: pd.DataFrame, universe: str) -> pd.DataFrame:
    """Take large names plus an even spread down the sector weight ranking.

    Pure top-weight sampling is good for weighted supply but poor for issuance breadth.
    This hybrid keeps roughly half the sample in the largest names and spreads the rest
    across the remaining capitalization ranks.
    """
    cap = MAX_NAMES_PER_SECTOR[universe]
    x = df.copy()
    if universe == "US":
        x = x[x["Location"].eq("United States")]
    elif universe == "EX_US":
        x = x[~x["Location"].eq("United States")]
    x = x[x["Weight (%)"].notna() & (x["Weight (%)"] > 0)].copy()
    x = x.drop_duplicates(subset=["Ticker", "ISIN"], keep="first")

    chunks = []
    for _, g in x.groupby("Sector"):
        g = g.sort_values("Weight (%)", ascending=False).reset_index(drop=True)
        if len(g) <= cap:
            chunks.append(g)
            continue
        top_n = max(10, cap // 2)
        top = g.head(top_n)
        rest = g.iloc[top_n:].copy()
        need = cap - len(top)
        if need > 0 and len(rest):
            idx = np.linspace(0, len(rest) - 1, num=min(need, len(rest)), dtype=int)
            spread = rest.iloc[np.unique(idx)]
            chunks.append(pd.concat([top, spread], ignore_index=True))
        else:
            chunks.append(top)

    sampled = pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame(columns=x.columns)
    sampled["universe"] = universe
    sampled["yahoo_ticker"] = sampled.apply(to_yahoo_ticker, axis=1)
    sampled = sampled[sampled["yahoo_ticker"].notna()].copy()
    return sampled


def _clean_share_series(s) -> pd.Series:
    if s is None or len(s) == 0:
        return pd.Series(dtype=float)
    s = pd.Series(s).copy()
    s.index = pd.to_datetime(s.index, utc=True, errors="coerce").tz_convert(None)
    s = pd.to_numeric(s, errors="coerce").dropna().sort_index()
    s = s[s > 0]
    return s[~s.index.duplicated(keep="last")]


def _shares_from_statements(t: yf.Ticker) -> pd.Series:
    """Fallback when Yahoo's shares endpoint is rate-limited.

    Quarterly/annual balance sheets frequently expose Ordinary Shares Number or
    Share Issued. The series is lower-frequency but sufficient for 3/6/12m supply.
    """
    candidates = ["Ordinary Shares Number", "Share Issued"]
    for attr in ["quarterly_balance_sheet", "balance_sheet"]:
        try:
            bs = getattr(t, attr)
            if bs is None or getattr(bs, "empty", True):
                continue
            for item in candidates:
                if item in bs.index:
                    raw = bs.loc[item].dropna()
                    if len(raw):
                        raw.index = pd.to_datetime(raw.index, errors="coerce")
                        raw = pd.to_numeric(raw, errors="coerce").dropna().sort_index()
                        raw = raw[raw > 0]
                        if len(raw):
                            return raw
        except Exception:
            continue
    return pd.Series(dtype=float)


def _fetch_shares_series(yahoo_ticker: str, start: pd.Timestamp) -> pd.Series:
    last_exc = None
    t = yf.Ticker(yahoo_ticker)
    for attempt in range(3):
        try:
            s = _clean_share_series(t.get_shares_full(start=start.date().isoformat()))
            if len(s):
                return s
        except Exception as exc:
            last_exc = exc
        time.sleep(0.8 * (attempt + 1))

    # Important for GitHub Actions: Yahoo often throttles get_shares_full before
    # it throttles statement data, so use statements as a second source.
    s = _shares_from_statements(t)
    if len(s):
        return s
    return pd.Series(dtype=float)


def _fetch_split_table(tickers: list[str], start: pd.Timestamp) -> dict[str, pd.Series]:
    out: dict[str, pd.Series] = {t: pd.Series(dtype=float) for t in tickers}
    if not tickers:
        return out
    try:
        data = yf.download(
            tickers=tickers,
            start=start.date().isoformat(),
            auto_adjust=False,
            actions=True,
            progress=False,
            threads=True,
            group_by="column",
        )
        if data.empty:
            return out
        if isinstance(data.columns, pd.MultiIndex):
            if "Stock Splits" in data.columns.get_level_values(0):
                splits = data["Stock Splits"]
                for t in tickers:
                    if t in splits.columns:
                        s = pd.to_numeric(splits[t], errors="coerce")
                        s.index = pd.to_datetime(s.index, utc=True, errors="coerce").tz_convert(None)
                        out[t] = s[(s.notna()) & (s != 0)]
        elif "Stock Splits" in data.columns and len(tickers) == 1:
            s = pd.to_numeric(data["Stock Splits"], errors="coerce")
            s.index = pd.to_datetime(s.index, utc=True, errors="coerce").tz_convert(None)
            out[tickers[0]] = s[(s.notna()) & (s != 0)]
    except Exception:
        pass
    return out


def _share_change(s: pd.Series, splits: pd.Series, days: int) -> tuple[float, pd.Timestamp | None]:
    if s.empty:
        return np.nan, None
    now_date = s.index.max()
    now_val = float(s.iloc[-1])
    target = now_date - pd.Timedelta(days=days)
    past = s.loc[:target]
    if past.empty:
        return np.nan, None
    baseline_date = past.index.max()
    # Require a reasonably nearby historical observation; stale share counts are misleading.
    if (target - baseline_date).days > 120:
        return np.nan, baseline_date
    baseline = float(past.iloc[-1])

    if not splits.empty:
        relevant = splits[(splits.index > baseline_date) & (splits.index <= now_date)]
        if len(relevant):
            factor = float(np.prod(pd.to_numeric(relevant, errors="coerce").dropna()))
            if factor > 0 and math.isfinite(factor):
                baseline *= factor

    if baseline <= 0 or now_val <= 0:
        return np.nan, baseline_date
    return now_val / baseline - 1, baseline_date


def _weighted_mean(values: pd.Series, weights: pd.Series) -> float:
    mask = values.notna() & weights.notna() & (weights > 0)
    if not mask.any():
        return np.nan
    return float(np.average(values[mask], weights=weights[mask]))


def _aggregate(details: pd.DataFrame, full_holdings: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    as_of = pd.Timestamp.utcnow().date().isoformat()
    for (universe, sector), g in details.groupby(["universe", "Sector"]):
        src = full_holdings["GLOBAL" if universe in {"GLOBAL", "EX_US"} else "US"]
        if universe == "US":
            src = src[src["Location"].eq("United States")]
        elif universe == "EX_US":
            src = src[~src["Location"].eq("United States")]
        sector_total_weight = float(src.loc[src["Sector"].eq(sector), "Weight (%)"].sum())
        valid_weight = float(g.loc[g["change_12m"].notna(), "Weight (%)"].sum())
        row = {
            "as_of": as_of,
            "universe": universe,
            "sector": sector,
            "sector_ko": SECTOR_KOR.get(sector, sector),
            "n_sample": int(len(g)),
            "n_valid_12m": int(g["change_12m"].notna().sum()),
            "sector_weight_pct": sector_total_weight,
            "valid_weight_pct": valid_weight,
            "coverage_of_sector_weight": (valid_weight / sector_total_weight) if sector_total_weight > 0 else np.nan,
        }
        for h in CHANGE_HORIZONS:
            c = f"change_{h}"
            valid = g[c].dropna()
            row[f"median_change_{h}"] = float(valid.median()) if len(valid) else np.nan
            row[f"weighted_change_{h}"] = _weighted_mean(g[c], g["Weight (%)"])
            row[f"pct_increasing_{h}"] = float((valid > ISSUANCE_THRESHOLD).mean()) if len(valid) else np.nan
            row[f"pct_decreasing_{h}"] = float((valid < -ISSUANCE_THRESHOLD).mean()) if len(valid) else np.nan
            row[f"net_breadth_{h}"] = (
                row[f"pct_increasing_{h}"] - row[f"pct_decreasing_{h}"]
                if pd.notna(row[f"pct_increasing_{h}"]) and pd.notna(row[f"pct_decreasing_{h}"])
                else np.nan
            )

        w12 = row["weighted_change_12m"]
        breadth12 = row["net_breadth_12m"]
        if pd.notna(w12) and pd.notna(breadth12):
            if w12 >= 0.02 and breadth12 >= 0.15:
                signal = "공급 증가"
            elif w12 <= -0.02 and breadth12 <= -0.15:
                signal = "공급 감소"
            elif w12 >= 0.01:
                signal = "완만한 공급 증가"
            elif w12 <= -0.01:
                signal = "완만한 공급 감소"
            else:
                signal = "중립"
        else:
            signal = "데이터 부족"
        row["signal"] = signal
        rows.append(row)
    return pd.DataFrame(rows)


def _append_history(latest: pd.DataFrame) -> None:
    path = OUT / "stock_supply_sector_history.csv"
    if path.exists():
        try:
            old = pd.read_csv(path)
        except Exception:
            old = pd.DataFrame()
        hist = pd.concat([old, latest], ignore_index=True)
    else:
        hist = latest.copy()
    if not hist.empty:
        hist = hist.drop_duplicates(subset=["as_of", "universe", "sector"], keep="last")
        hist = hist.sort_values(["as_of", "universe", "sector"])
    hist.to_csv(path, index=False)


def _write_empty_if_needed() -> None:
    latest = OUT / "stock_supply_sector_latest.csv"
    detail = OUT / "stock_supply_company_detail.csv"
    history = OUT / "stock_supply_sector_history.csv"
    if not latest.exists():
        pd.DataFrame(columns=[
            "as_of","universe","sector","sector_ko","n_sample","n_valid_12m",
            "sector_weight_pct","valid_weight_pct","coverage_of_sector_weight",
            "median_change_3m","weighted_change_3m","pct_increasing_3m","pct_decreasing_3m","net_breadth_3m",
            "median_change_6m","weighted_change_6m","pct_increasing_6m","pct_decreasing_6m","net_breadth_6m",
            "median_change_12m","weighted_change_12m","pct_increasing_12m","pct_decreasing_12m","net_breadth_12m",
            "signal",
        ]).to_csv(latest, index=False)
    if not detail.exists():
        pd.DataFrame().to_csv(detail, index=False)
    if not history.exists():
        pd.DataFrame().to_csv(history, index=False)


def _prior_output_is_fresh() -> bool:
    p = OUT / "stock_supply_sector_latest.csv"
    if not p.exists():
        return False
    try:
        df = pd.read_csv(p)
        if df.empty or "as_of" not in df.columns:
            return False
        last = pd.to_datetime(df["as_of"], errors="coerce").max()
        if pd.isna(last):
            return False
        age = (pd.Timestamp.utcnow().tz_localize(None).normalize() - last.normalize()).days
        return age < MIN_REFRESH_DAYS
    except Exception:
        return False


def main() -> None:
    if _prior_output_is_fresh():
        print(f"Stock-supply proxy is < {MIN_REFRESH_DAYS} days old; keeping prior snapshot.")
        return
    print("Fetching US and global equity-supply proxy...")
    us = _read_ishares_csv(HOLDINGS_URLS["US"], RAW / "ivv_holdings_latest.csv", "IVV")
    global_df = _read_ishares_csv(HOLDINGS_URLS["GLOBAL"], RAW / "acwi_holdings_latest.csv", "ACWI")

    samples = pd.concat([
        _sample_holdings(us, "US"),
        _sample_holdings(global_df, "GLOBAL"),
        _sample_holdings(global_df, "EX_US"),
    ], ignore_index=True)
    print(f"Sampled holdings: {len(samples)} rows across US / GLOBAL / EX_US")
    print("Sample counts:", samples.groupby("universe").size().to_dict())
    print("Mapped Yahoo tickers:", int(samples["yahoo_ticker"].notna().sum()))
    if samples.empty:
        raise RuntimeError("No holdings survived ticker mapping; check Location/Exchange mappings.")

    # Same issuer can occur in multiple universes. Fetch each Yahoo series only once.
    tickers = sorted(samples["yahoo_ticker"].dropna().unique().tolist())
    start = pd.Timestamp.utcnow().tz_localize(None) - pd.Timedelta(days=LOOKBACK_DAYS)
    split_map = _fetch_split_table(tickers, start)

    series_cache: dict[str, pd.Series] = {}
    rows = []
    total = len(tickers)
    for idx, t in enumerate(tickers, 1):
        s = _fetch_shares_series(t, start)
        series_cache[t] = s
        if idx % 25 == 0 or idx == total:
            print(f"  shares: {idx}/{total}")
        time.sleep(0.15)

    for _, r in samples.iterrows():
        t = r["yahoo_ticker"]
        s = series_cache.get(t, pd.Series(dtype=float))
        item = {
            "as_of": pd.Timestamp.utcnow().date().isoformat(),
            "universe": r["universe"],
            "ticker": r["Ticker"],
            "yahoo_ticker": t,
            "name": r["Name"],
            "Sector": r["Sector"],
            "sector_ko": SECTOR_KOR.get(r["Sector"], r["Sector"]),
            "location": r["Location"],
            "exchange": r["Exchange"],
            "isin": r["ISIN"],
            "Weight (%)": r["Weight (%)"],
            "latest_shares": float(s.iloc[-1]) if len(s) else np.nan,
            "latest_shares_date": s.index.max().date().isoformat() if len(s) else None,
        }
        for h, days in CHANGE_HORIZONS.items():
            chg, base_date = _share_change(s, split_map.get(t, pd.Series(dtype=float)), days)
            item[f"change_{h}"] = chg
            item[f"baseline_date_{h}"] = base_date.date().isoformat() if base_date is not None else None
        rows.append(item)

    detail = pd.DataFrame(rows)
    valid = int(detail["change_12m"].notna().sum()) if len(detail) else 0
    valid_ratio = valid / len(detail) if len(detail) else 0.0

    # Do not overwrite a previously good snapshot when Yahoo is broadly rate-limited.
    prior_path = OUT / "stock_supply_sector_latest.csv"
    prior_good = False
    if prior_path.exists():
        try:
            prior_good = not pd.read_csv(prior_path).empty
        except Exception:
            prior_good = False
    if valid_ratio < 0.20 and prior_good:
        print(f"WARNING: only {valid}/{len(detail)} rows have 12m data; keeping prior stock-supply snapshot.")
        return
    if valid_ratio < 0.20:
        print(f"WARNING: only {valid}/{len(detail)} rows have 12m data. Writing partial snapshot so coverage is visible in the dashboard.")

    detail.to_csv(OUT / "stock_supply_company_detail.csv", index=False)
    latest = _aggregate(detail, {"US": us, "GLOBAL": global_df})
    if latest.empty:
        raise RuntimeError("Stock-supply aggregation produced 0 sector rows; refusing to write an empty latest file.")
    latest.to_csv(OUT / "stock_supply_sector_latest.csv", index=False)
    _append_history(latest)

    print(f"Stock-supply proxy updated: {valid}/{len(detail)} sampled rows have 12m share-count data.")


if __name__ == "__main__":
    main()

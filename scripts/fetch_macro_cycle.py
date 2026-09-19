from __future__ import annotations

from io import StringIO
from pathlib import Path
import re
import warnings

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
PROCESSED.mkdir(parents=True, exist_ok=True)

LATEST_PATH = PROCESSED / "macro_cycle_latest.csv"
HISTORY_PATH = PROCESSED / "macro_cycle_history.csv"

HEADERS = {
    "User-Agent": "MarketLeadershipDashboard/1.0 (+https://github.com/horea457/Market-leadership)",
    "Accept-Language": "en-US,en;q=0.9",
}

DISPLAY_AREAS = {
    "GLOBAL": "글로벌",
    "USA": "미국",
    "EUR": "유럽",
    "GBR": "영국",
    "JPN": "일본",
    "KOR": "한국",
    "CHN": "중국",
    "BRA": "브라질",
}

CLI_SOURCE = {
    "GLOBAL": "G20",
    "USA": "USA",
    "EUR": "G4E",   # OECD Major four European countries
    "GBR": "GBR",
    "JPN": "JPN",
    "KOR": "KOR",
    "CHN": "CHN",
    "BRA": "BRA",
}

CURVE_SOURCE = {
    "USA": "USA",
    "EUR": "DEU",   # euro-area local-rate proxy: Germany long rate vs euro short rate
    "GBR": "GBR",
    "JPN": "JPN",
    "KOR": "KOR",
    "CHN": "CHN",
    "BRA": "BRA",
}

PMI_SOURCE_NAME = {
    "USA": "United States",
    "EUR": "Euro Area",
    "GBR": "United Kingdom",
    "JPN": "Japan",
    "KOR": "South Korea",
    "CHN": "China",
    "BRA": "Brazil",
}

OECD_CLI_URL = (
    "https://sdmx.oecd.org/public/rest/data/"
    "OECD.SDD.STES,DSD_STES@DF_CLI,4.1/"
    "{areas}.M.LI...AA...H"
    "?startPeriod=2018-01&dimensionAtObservation=AllDimensions"
)

OECD_FIN_URL = (
    "https://sdmx.oecd.org/public/rest/data/"
    "OECD.SDD.STES,DSD_STES@DF_FINMARK,4.0/"
    "{areas}.M.IRLT+IR3TIB+IRSTCI.PA....."
    "?startPeriod=2018-01&dimensionAtObservation=AllDimensions"
)

PMI_TABLE_URL = "https://tradingeconomics.com/country-list/manufacturing-pmi?continent=g20"
FRED_CURVE_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=T10Y2Y"


def _http_text(url: str, accept: str | None = None, timeout: int = 35) -> str:
    headers = dict(HEADERS)
    if accept:
        headers["Accept"] = accept
    r = requests.get(url, headers=headers, timeout=timeout)
    r.raise_for_status()
    return r.text


def _read_oecd_csv(url: str) -> pd.DataFrame:
    text = _http_text(url, accept="text/csv")
    if not text.strip():
        return pd.DataFrame()
    return pd.read_csv(StringIO(text))


def _col(df: pd.DataFrame, *names: str) -> str | None:
    if df is None or df.empty:
        return None
    direct = {str(c): c for c in df.columns}
    lower = {str(c).strip().lower(): c for c in df.columns}
    for n in names:
        if n in direct:
            return direct[n]
        if n.strip().lower() in lower:
            return lower[n.strip().lower()]
    return None


def _normalise_sdmx(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["source_area", "measure", "date", "value"])

    area_c = _col(df, "REF_AREA", "Reference area")
    measure_c = _col(df, "MEASURE", "Measure")
    period_c = _col(df, "TIME_PERIOD", "Time period")
    value_c = _col(df, "OBS_VALUE", "Observation value", "Value")

    if period_c is None or value_c is None:
        raise ValueError(f"OECD response columns not recognised: {list(df.columns)[:20]}")

    out = pd.DataFrame({
        "source_area": df[area_c].astype(str) if area_c else "",
        "measure": df[measure_c].astype(str) if measure_c else "",
        "date": pd.to_datetime(df[period_c].astype(str), errors="coerce"),
        "value": pd.to_numeric(df[value_c], errors="coerce"),
    })
    return out.dropna(subset=["date", "value"]).sort_values(["source_area", "measure", "date"])


def fetch_cli() -> pd.DataFrame:
    areas = "+".join(sorted(set(CLI_SOURCE.values())))
    raw = _read_oecd_csv(OECD_CLI_URL.format(areas=areas))
    x = _normalise_sdmx(raw)
    if x.empty:
        return x
    return x[["source_area", "date", "value"]].rename(columns={"value": "cli"})


def fetch_curve_oecd() -> pd.DataFrame:
    areas = "+".join(sorted(set(CURVE_SOURCE.values())))
    raw = _read_oecd_csv(OECD_FIN_URL.format(areas=areas))
    x = _normalise_sdmx(raw)
    if x.empty:
        return pd.DataFrame(columns=["source_area", "date", "long_rate", "short_rate", "curve_spread"])

    # Some CSV flavours expose code labels; others expose human-readable measure labels.
    m = x["measure"].astype(str)
    is_long = m.str.contains(r"IRLT|Long-term", case=False, regex=True)
    is_short3m = m.str.contains(r"IR3TIB|Short-term", case=False, regex=True)
    is_short_call = m.str.contains(r"IRSTCI|Immediate", case=False, regex=True)

    long = (
        x[is_long]
        .sort_values("date")
        .drop_duplicates(["source_area", "date"], keep="last")
        [["source_area", "date", "value"]]
        .rename(columns={"value": "long_rate"})
    )
    short3m = (
        x[is_short3m]
        .sort_values("date")
        .drop_duplicates(["source_area", "date"], keep="last")
        [["source_area", "date", "value"]]
        .rename(columns={"value": "short_3m"})
    )
    shortcall = (
        x[is_short_call]
        .sort_values("date")
        .drop_duplicates(["source_area", "date"], keep="last")
        [["source_area", "date", "value"]]
        .rename(columns={"value": "short_call"})
    )

    out = long.merge(short3m, on=["source_area", "date"], how="outer")
    out = out.merge(shortcall, on=["source_area", "date"], how="outer")
    out["short_rate"] = out["short_3m"].combine_first(out["short_call"])
    out["curve_spread"] = out["long_rate"] - out["short_rate"]
    return out[["source_area", "date", "long_rate", "short_rate", "curve_spread"]].sort_values(
        ["source_area", "date"]
    )


def fetch_us_daily_curve() -> pd.DataFrame:
    try:
        text = _http_text(FRED_CURVE_URL)
        x = pd.read_csv(StringIO(text))
        if x.shape[1] < 2:
            return pd.DataFrame()
        x.columns = ["date", "us_10y2y"]
        x["date"] = pd.to_datetime(x["date"], errors="coerce")
        x["us_10y2y"] = pd.to_numeric(x["us_10y2y"], errors="coerce")
        return x.dropna().sort_values("date")
    except Exception as exc:
        warnings.warn(f"FRED T10Y2Y unavailable: {exc}")
        return pd.DataFrame()


def _parse_pmi_table() -> pd.DataFrame:
    html = _http_text(PMI_TABLE_URL, accept="text/html,application/xhtml+xml")
    tables = pd.read_html(StringIO(html))
    for t in tables:
        cols = {str(c).strip().lower(): c for c in t.columns}
        def pick(prefix):
            return next((orig for low, orig in cols.items() if low.startswith(prefix)), None)
        country_c = pick("country")
        last_c = pick("last")
        previous_c = pick("previous")
        reference_c = pick("reference")
        if all(v is not None for v in [country_c, last_c, previous_c, reference_c]):
            out = t.rename(columns={
                country_c: "country",
                last_c: "pmi",
                previous_c: "pmi_previous",
                reference_c: "reference",
            }).copy()
            out["country"] = out["country"].astype(str).str.strip()
            out["pmi"] = pd.to_numeric(out["pmi"], errors="coerce")
            out["pmi_previous"] = pd.to_numeric(out["pmi_previous"], errors="coerce")
            out["reference"] = out["reference"].astype(str).str.strip()
            return out.dropna(subset=["pmi"])
    raise ValueError("Manufacturing PMI table not found")


def _parse_reference_period(ref: str) -> pd.Timestamp:
    m = re.search(r"([A-Za-z]{3})\s*/\s*(\d{2,4})", str(ref))
    if not m:
        return pd.NaT
    mon, yr = m.groups()
    year = int(yr)
    if year < 100:
        year += 2000
    try:
        return pd.to_datetime(f"01-{mon}-{year}", format="%d-%b-%Y")
    except Exception:
        return pd.NaT


def fetch_pmi() -> pd.DataFrame:
    try:
        table = _parse_pmi_table()
    except Exception as exc:
        warnings.warn(f"PMI table unavailable: {exc}")
        return pd.DataFrame(columns=["area_code", "date", "pmi", "pmi_previous", "pmi_source"])

    rows = []
    for area_code, country in PMI_SOURCE_NAME.items():
        z = table[table["country"].str.casefold().eq(country.casefold())]
        if z.empty:
            continue
        r = z.iloc[0]
        rows.append({
            "area_code": area_code,
            "date": _parse_reference_period(r.get("reference")),
            "pmi": r.get("pmi"),
            "pmi_previous": r.get("pmi_previous"),
            "pmi_source": "Trading Economics public headline table; underlying survey provider varies",
        })

    # A simple cross-country summary is deliberately labelled median/breadth,
    # not the proprietary S&P/J.P.Morgan Global PMI.
    vals = pd.to_numeric(table["pmi"], errors="coerce").dropna()
    if len(vals):
        refs = table["reference"].map(_parse_reference_period).dropna()
        rows.append({
            "area_code": "GLOBAL",
            "date": refs.max() if len(refs) else pd.NaT,
            "pmi": float(vals.median()),
            "pmi_previous": float(pd.to_numeric(table["pmi_previous"], errors="coerce").median()),
            "pmi_source": "Major-economy manufacturing PMI median (not proprietary Global PMI)",
        })
    return pd.DataFrame(rows)


def _direction_label(value, delta, pivot):
    if pd.isna(value):
        return "데이터 없음"
    d = 0 if pd.isna(delta) else float(delta)
    if value >= pivot and d > 0:
        return "상단·상승"
    if value >= pivot and d < 0:
        return "상단·둔화"
    if value < pivot and d > 0:
        return "하단·개선"
    if value < pivot and d < 0:
        return "하단·악화"
    return "횡보"


def _pmi_label(value, delta):
    if pd.isna(value):
        return "데이터 없음"
    d = 0 if pd.isna(delta) else float(delta)
    if value >= 50 and d > 0:
        return "확장 가속"
    if value >= 50 and d < 0:
        return "확장 둔화"
    if value < 50 and d > 0:
        return "수축 완화"
    if value < 50 and d < 0:
        return "수축 심화"
    return "확장" if value >= 50 else "수축"


def _curve_label(spread, delta):
    if pd.isna(spread):
        return "데이터 없음"
    d = 0 if pd.isna(delta) else float(delta)
    if spread >= 0 and d > 0:
        return "정상·스티프닝"
    if spread >= 0 and d < 0:
        return "정상·플래트닝"
    if spread < 0 and d > 0:
        return "역전·정상화"
    if spread < 0 and d < 0:
        return "역전 심화"
    return "정상" if spread >= 0 else "역전"


def _safe_previous_history() -> pd.DataFrame:
    if not HISTORY_PATH.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(HISTORY_PATH)
    except Exception:
        return pd.DataFrame()


def build_history(cli: pd.DataFrame, curve: pd.DataFrame, pmi: pd.DataFrame, us_daily: pd.DataFrame) -> pd.DataFrame:
    frames = []

    # CLI full history -> display codes
    for display_code, source_code in CLI_SOURCE.items():
        z = cli[cli["source_area"].astype(str).eq(source_code)].copy()
        if z.empty:
            continue
        z["area_code"] = display_code
        z = z[["date", "area_code", "cli"]]
        frames.append(z)

    # Curve full history -> display codes
    curve_frames = []
    for display_code, source_code in CURVE_SOURCE.items():
        z = curve[curve["source_area"].astype(str).eq(source_code)].copy()
        if z.empty:
            continue
        z["area_code"] = display_code
        curve_frames.append(z[["date", "area_code", "long_rate", "short_rate", "curve_spread"]])

    cli_hist = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["date", "area_code", "cli"])
    curve_hist = pd.concat(curve_frames, ignore_index=True) if curve_frames else pd.DataFrame(
        columns=["date", "area_code", "long_rate", "short_rate", "curve_spread"]
    )

    hist = cli_hist.merge(curve_hist, on=["date", "area_code"], how="outer")

    # Global curve = cross-country median. This is a dashboard summary, not a traded curve.
    if not curve_hist.empty:
        g = (
            curve_hist.groupby("date", as_index=False)
            .agg(long_rate=("long_rate", "median"), short_rate=("short_rate", "median"), curve_spread=("curve_spread", "median"))
        )
        g["area_code"] = "GLOBAL"
        hist = pd.concat([hist, g], ignore_index=True, sort=False)

    # Override US curve with high-frequency 10Y-2Y on its monthly last observation.
    if us_daily is not None and not us_daily.empty:
        u = us_daily.copy()
        u["month"] = u["date"].dt.to_period("M").dt.to_timestamp()
        u = u.sort_values("date").groupby("month", as_index=False).tail(1)
        u = u[["month", "us_10y2y"]].rename(columns={"month": "date", "us_10y2y": "curve_spread"})
        u["area_code"] = "USA"
        for c in ["long_rate", "short_rate"]:
            u[c] = np.nan
        hist = hist[~((hist["area_code"] == "USA") & hist["date"].isin(u["date"]))]
        hist = pd.concat([hist, u], ignore_index=True, sort=False)

    # Current + previous PMI snapshots. Previous month is inferred from the headline table.
    pmi_rows = []
    if pmi is not None and not pmi.empty:
        for _, r in pmi.iterrows():
            dt = pd.to_datetime(r.get("date"), errors="coerce")
            if pd.isna(dt):
                continue
            pmi_rows.append({
                "date": dt.to_period("M").to_timestamp(),
                "area_code": r["area_code"],
                "pmi": r.get("pmi"),
                "pmi_source": r.get("pmi_source"),
            })
            prev = pd.to_numeric(pd.Series([r.get("pmi_previous")]), errors="coerce").iloc[0]
            if pd.notna(prev):
                pmi_rows.append({
                    "date": (dt - pd.offsets.MonthBegin(1)).to_period("M").to_timestamp(),
                    "area_code": r["area_code"],
                    "pmi": prev,
                    "pmi_source": r.get("pmi_source"),
                })

    pmi_hist = pd.DataFrame(pmi_rows)
    if not pmi_hist.empty:
        hist = hist.merge(pmi_hist, on=["date", "area_code"], how="outer")

    # Preserve PMI observations accumulated by prior weekly runs.
    old = _safe_previous_history()
    if not old.empty:
        old["date"] = pd.to_datetime(old["date"], errors="coerce")
        keep = [c for c in ["date", "area_code", "pmi", "pmi_source"] if c in old.columns]
        if len(keep) >= 3:
            prior_pmi = old[keep].dropna(subset=["date", "area_code", "pmi"])
            hist = pd.concat([hist, prior_pmi], ignore_index=True, sort=False)

    hist["date"] = pd.to_datetime(hist["date"], errors="coerce")
    hist = hist.dropna(subset=["date", "area_code"]).sort_values(["area_code", "date"])

    # Consolidate fields from duplicate source rows.
    def last_valid(s):
        z = s.dropna()
        return z.iloc[-1] if len(z) else np.nan

    agg = {c: last_valid for c in hist.columns if c not in ["date", "area_code"]}
    hist = hist.groupby(["date", "area_code"], as_index=False).agg(agg)
    hist["area"] = hist["area_code"].map(DISPLAY_AREAS).fillna(hist["area_code"])
    return hist.sort_values(["area_code", "date"]).reset_index(drop=True)


def build_latest(hist: pd.DataFrame, pmi_raw: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for code, label in DISPLAY_AREAS.items():
        z = hist[hist["area_code"].eq(code)].sort_values("date")
        if z.empty:
            continue

        def latest_and_delta(col, periods=1):
            q = z[["date", col]].dropna()
            if q.empty:
                return np.nan, np.nan, pd.NaT
            latest = float(q.iloc[-1][col])
            prev = float(q.iloc[-1 - periods][col]) if len(q) > periods else np.nan
            return latest, latest - prev if pd.notna(prev) else np.nan, q.iloc[-1]["date"]

        pmi, pmi_delta, pmi_date = latest_and_delta("pmi")
        cli, cli_delta, cli_date = latest_and_delta("cli")
        curve, curve_delta, curve_date = latest_and_delta("curve_spread")

        qcurve = z.dropna(subset=["curve_spread"])
        long_rate = qcurve.iloc[-1].get("long_rate") if len(qcurve) else np.nan
        short_rate = qcurve.iloc[-1].get("short_rate") if len(qcurve) else np.nan

        pmi_source = ""
        if pmi_raw is not None and not pmi_raw.empty:
            pr = pmi_raw[pmi_raw["area_code"].eq(code)]
            if len(pr):
                pmi_source = str(pr.iloc[-1].get("pmi_source", ""))

        rows.append({
            "area_code": code,
            "area": label,
            "pmi": pmi,
            "pmi_1m_change": pmi_delta,
            "pmi_state": _pmi_label(pmi, pmi_delta),
            "pmi_period": pmi_date.strftime("%Y-%m") if pd.notna(pmi_date) else "",
            "pmi_source": pmi_source,
            "cli": cli,
            "cli_1m_change": cli_delta,
            "cli_state": _direction_label(cli, cli_delta, 100.0),
            "cli_period": cli_date.strftime("%Y-%m") if pd.notna(cli_date) else "",
            "curve_spread": curve,
            "curve_1m_change": curve_delta,
            "curve_state": _curve_label(curve, curve_delta),
            "curve_period": curve_date.strftime("%Y-%m") if pd.notna(curve_date) else "",
            "long_rate": long_rate,
            "short_rate": short_rate,
        })

    out = pd.DataFrame(rows)

    # PMI breadth is meaningful only as a cross-country participation measure.
    locals_only = out[out["area_code"].ne("GLOBAL")].dropna(subset=["pmi"])
    breadth = float((locals_only["pmi"] >= 50).mean()) if len(locals_only) else np.nan
    if "GLOBAL" in out["area_code"].values:
        out.loc[out["area_code"].eq("GLOBAL"), "pmi_breadth_above_50"] = breadth
    else:
        out["pmi_breadth_above_50"] = np.nan
    return out


def main():
    print("Fetching macro-cycle layer (PMI / OECD CLI / yield curves)...", flush=True)

    try:
        cli = fetch_cli()
    except Exception as exc:
        warnings.warn(f"OECD CLI fetch failed: {exc}")
        cli = pd.DataFrame(columns=["source_area", "date", "cli"])

    try:
        curve = fetch_curve_oecd()
    except Exception as exc:
        warnings.warn(f"OECD curve fetch failed: {exc}")
        curve = pd.DataFrame(columns=["source_area", "date", "long_rate", "short_rate", "curve_spread"])

    pmi = fetch_pmi()
    us_daily = fetch_us_daily_curve()

    hist = build_history(cli, curve, pmi, us_daily)

    if hist.empty:
        # Do not destroy a previously valid dashboard just because a public endpoint had a bad day.
        if HISTORY_PATH.exists() and LATEST_PATH.exists():
            print("Macro endpoints unavailable; keeping prior processed files.", flush=True)
            return
        raise RuntimeError("No macro-cycle data could be retrieved and no prior cache exists.")

    latest = build_latest(hist, pmi)

    hist_out = hist.copy()
    hist_out["date"] = pd.to_datetime(hist_out["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    hist_out.to_csv(HISTORY_PATH, index=False)
    latest.to_csv(LATEST_PATH, index=False)

    print(
        f"Macro-cycle layer updated: {len(latest)} areas, "
        f"{len(hist_out)} history rows.",
        flush=True,
    )


if __name__ == "__main__":
    main()

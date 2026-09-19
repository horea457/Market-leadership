from pathlib import Path
from io import StringIO
import time
import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

LATEST_PATH = OUT / "credit_cycle_latest.csv"
HISTORY_PATH = OUT / "credit_cycle_history.csv"

FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
HEADERS = {
    "User-Agent": "MarketLeadershipDashboard/1.0 (+https://github.com/horea457/Market-leadership)"
}

SERIES = {
    "sloos_tightening": {
        "id": "DRTSCILM",
        "label": "SLOOS C&I 대출기준 강화 비율",
        "group": "신용 공급의지",
        "unit": "%",
    },
    "bank_loan_growth": {
        "id": "H8B1020NCBCMG",
        "label": "은행 Loans & Leases 증가율",
        "group": "신용량",
        "unit": "% annualized",
    },
    "corp_debt_level": {
        "id": "BCNSDODNS",
        "label": "비금융기업 Debt Securities + Loans",
        "group": "Broad credit",
        "unit": "$mn SAAR",
    },
    "hy_oas": {
        "id": "BAMLH0A0HYM2",
        "label": "US High Yield OAS",
        "group": "신용가격",
        "unit": "%p",
    },
    "chargeoff": {
        "id": "CORBLACBS",
        "label": "Business Loan Charge-off Rate",
        "group": "신용손실",
        "unit": "%",
    },
    "delinquency": {
        "id": "DRBLACBS",
        "label": "Business Loan Delinquency Rate",
        "group": "신용손실",
        "unit": "%",
    },
}


def fetch_fred(series_id, attempts=3):
    url = FRED_URL.format(series=series_id)
    last = None
    for attempt in range(attempts):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            df = pd.read_csv(StringIO(r.text))
            if len(df.columns) < 2:
                raise ValueError(f"Unexpected FRED response for {series_id}")
            df = df.rename(columns={df.columns[0]: "date", df.columns[1]: "value"})
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df["value"] = pd.to_numeric(df["value"], errors="coerce")
            df = df.dropna(subset=["date", "value"]).sort_values("date")
            if df.empty:
                raise ValueError(f"No observations for {series_id}")
            return df
        except Exception as exc:
            last = exc
            if attempt < attempts - 1:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"FRED {series_id} unavailable: {last}")


def latest_delta(df, periods=1):
    x = df.dropna(subset=["value"]).sort_values("date")
    if x.empty:
        return np.nan, np.nan, pd.NaT
    latest = float(x.iloc[-1]["value"])
    prev = float(x.iloc[-1 - periods]["value"]) if len(x) > periods else np.nan
    delta = latest - prev if np.isfinite(prev) else np.nan
    return latest, delta, x.iloc[-1]["date"]


def yoy_change(df):
    x = df.dropna(subset=["value"]).sort_values("date").copy()
    if x.empty:
        return np.nan, np.nan
    latest = float(x.iloc[-1]["value"])
    cutoff = x.iloc[-1]["date"] - pd.DateOffset(months=12)
    prev = x[x["date"] <= cutoff]
    if prev.empty:
        return np.nan, np.nan
    base = float(prev.iloc[-1]["value"])
    if base == 0:
        return np.nan, np.nan
    return (latest / base - 1.0) * 100.0, base


def percentile_recent(df, years=5):
    x = df.dropna(subset=["value"]).sort_values("date")
    if x.empty:
        return np.nan
    cutoff = x.iloc[-1]["date"] - pd.DateOffset(years=years)
    y = x[x["date"] >= cutoff]["value"].dropna()
    if y.empty:
        return np.nan
    latest = float(y.iloc[-1])
    return float((y <= latest).mean())


def sloos_state(v, d):
    if not np.isfinite(v):
        return "데이터 없음"
    if v < 0:
        return "대출기준 순완화"
    if abs(v) < 1e-9:
        return "순긴축 해소" if np.isfinite(d) and d < 0 else "대출기준 중립"
    if np.isfinite(d) and d <= -5:
        return "긴축 완화중"
    if np.isfinite(d) and d >= 5:
        return "긴축 강화"
    return "대출기준 긴축"


def growth_state(v, d):
    if not np.isfinite(v):
        return "데이터 없음"
    if v > 0 and np.isfinite(d) and d > 0:
        return "신용 증가 가속"
    if v > 0:
        return "신용 증가"
    if np.isfinite(d) and d > 0:
        return "감소폭 완화"
    return "신용 감소"


def spread_state(v, d, pct):
    if not np.isfinite(v):
        return "데이터 없음"
    if np.isfinite(pct) and pct >= 0.80:
        return "신용가격 스트레스"
    if np.isfinite(d) and d >= 0.50:
        return "스프레드 확대"
    if np.isfinite(d) and d <= -0.50:
        return "스프레드 축소"
    return "스프레드 안정"


def loss_state(v, yoy_delta):
    if not np.isfinite(v):
        return "데이터 없음"
    if np.isfinite(yoy_delta) and yoy_delta >= 0.25:
        return "부실 상승"
    if np.isfinite(yoy_delta) and yoy_delta <= -0.25:
        return "부실 개선"
    return "부실 안정"


def main():
    print("Fetching U.S. credit-cycle layer...", flush=True)
    raw = {}
    errors = []
    for code, meta in SERIES.items():
        try:
            raw[code] = fetch_fred(meta["id"])
            print(f"  OK {meta['id']}: {len(raw[code])} rows", flush=True)
        except Exception as exc:
            errors.append(f"{meta['id']}: {exc}")
            print(f"  WARN {meta['id']}: {exc}", flush=True)

    if not raw:
        if LATEST_PATH.exists() and HISTORY_PATH.exists():
            print("All credit endpoints unavailable; keeping prior processed files.", flush=True)
            return
        pd.DataFrame(columns=["date", "metric_code", "metric", "group", "value", "unit", "source_series"]).to_csv(HISTORY_PATH, index=False)
        pd.DataFrame(columns=["as_of", "credit_state"]).to_csv(LATEST_PATH, index=False)
        return

    hist_parts = []
    for code, df in raw.items():
        meta = SERIES[code]
        h = df.copy()
        h["metric_code"] = code
        h["metric"] = meta["label"]
        h["group"] = meta["group"]
        h["unit"] = meta["unit"]
        h["source_series"] = meta["id"]
        hist_parts.append(h[["date", "metric_code", "metric", "group", "value", "unit", "source_series"]])

    history = pd.concat(hist_parts, ignore_index=True).sort_values(["date", "metric_code"])
    history.to_csv(HISTORY_PATH, index=False)

    def ld(code, periods=1):
        if code not in raw:
            return np.nan, np.nan, pd.NaT
        return latest_delta(raw[code], periods)

    sloos, sloos_qoq, sloos_date = ld("sloos_tightening")
    bank_growth, bank_growth_mom, bank_date = ld("bank_loan_growth")
    hy, _, hy_date = ld("hy_oas")

    hy_1m = np.nan
    hy_pct5y = np.nan
    if "hy_oas" in raw:
        hy_df = raw["hy_oas"]
        latest_dt = hy_df.iloc[-1]["date"]
        prior = hy_df[hy_df["date"] <= latest_dt - pd.DateOffset(months=1)]
        if len(prior):
            hy_1m = float(hy_df.iloc[-1]["value"] - prior.iloc[-1]["value"])
        hy_pct5y = percentile_recent(hy_df, 5)

    corp_yoy = np.nan
    corp_level = np.nan
    corp_date = pd.NaT
    if "corp_debt_level" in raw:
        corp_df = raw["corp_debt_level"]
        corp_level = float(corp_df.iloc[-1]["value"])
        corp_date = corp_df.iloc[-1]["date"]
        corp_yoy, _ = yoy_change(corp_df)

    charge, _, charge_date = ld("chargeoff")
    delin, _, delin_date = ld("delinquency")

    def yoy_delta_points(code):
        if code not in raw:
            return np.nan
        df = raw[code].sort_values("date")
        if df.empty:
            return np.nan
        latest_dt = df.iloc[-1]["date"]
        prev = df[df["date"] <= latest_dt - pd.DateOffset(months=12)]
        if prev.empty:
            return np.nan
        return float(df.iloc[-1]["value"] - prev.iloc[-1]["value"])

    charge_yoy = yoy_delta_points("chargeoff")
    delin_yoy = yoy_delta_points("delinquency")

    supply_improving = (
        np.isfinite(sloos)
        and (sloos <= 0 or (np.isfinite(sloos_qoq) and sloos_qoq < 0))
    )
    supply_worsening = (
        np.isfinite(sloos)
        and sloos > 0
        and np.isfinite(sloos_qoq)
        and sloos_qoq > 0
    )
    quantity_positive = (
        (np.isfinite(bank_growth) and bank_growth > 0)
        and (not np.isfinite(corp_yoy) or corp_yoy > 0)
    )
    price_stress = (
        (np.isfinite(hy_pct5y) and hy_pct5y >= 0.80)
        or (np.isfinite(hy_1m) and hy_1m >= 0.50)
    )
    losses_rising = (
        (np.isfinite(charge_yoy) and charge_yoy >= 0.25)
        or (np.isfinite(delin_yoy) and delin_yoy >= 0.25)
    )

    if supply_improving and quantity_positive and not price_stress and not losses_rising:
        credit_state = "신용 확장 확인"
    elif (supply_worsening and price_stress) or losses_rising:
        credit_state = "신용 스트레스 강화"
    elif supply_improving and not price_stress:
        credit_state = "신용 여건 개선"
    elif quantity_positive and not price_stress:
        credit_state = "신용 증가 · 공급 혼합"
    else:
        credit_state = "신용 여건 혼합"

    dates = [d for d in [sloos_date, bank_date, corp_date, hy_date, charge_date, delin_date] if pd.notna(d)]
    as_of = max(dates).date().isoformat() if dates else pd.Timestamp.today().date().isoformat()

    row = {
        "as_of": as_of,
        "credit_state": credit_state,
        "sloos_tightening": sloos,
        "sloos_qoq_change": sloos_qoq,
        "sloos_state": sloos_state(sloos, sloos_qoq),
        "sloos_period": sloos_date.strftime("%Y-%m") if pd.notna(sloos_date) else "",
        "bank_loan_growth": bank_growth,
        "bank_loan_growth_mom": bank_growth_mom,
        "bank_loan_state": growth_state(bank_growth, bank_growth_mom),
        "bank_loan_period": bank_date.strftime("%Y-%m") if pd.notna(bank_date) else "",
        "corp_debt_level_mn": corp_level,
        "corp_debt_yoy": corp_yoy,
        "corp_debt_state": growth_state(corp_yoy, np.nan),
        "corp_debt_period": corp_date.strftime("%Y-%m") if pd.notna(corp_date) else "",
        "hy_oas": hy,
        "hy_oas_1m_change": hy_1m,
        "hy_oas_5y_percentile": hy_pct5y,
        "hy_oas_state": spread_state(hy, hy_1m, hy_pct5y),
        "hy_oas_period": hy_date.strftime("%Y-%m-%d") if pd.notna(hy_date) else "",
        "chargeoff_rate": charge,
        "chargeoff_yoy_change": charge_yoy,
        "chargeoff_state": loss_state(charge, charge_yoy),
        "chargeoff_period": charge_date.strftime("%Y-%m") if pd.notna(charge_date) else "",
        "delinquency_rate": delin,
        "delinquency_yoy_change": delin_yoy,
        "delinquency_state": loss_state(delin, delin_yoy),
        "delinquency_period": delin_date.strftime("%Y-%m") if pd.notna(delin_date) else "",
        "source_note": "Federal Reserve/FRED: SLOOS, H.8, Z.1, ICE BofA HY OAS, bank charge-off/delinquency",
        "errors": " | ".join(errors),
    }
    pd.DataFrame([row]).to_csv(LATEST_PATH, index=False)
    print(f"Credit-cycle state: {credit_state}", flush=True)
    print(f"Wrote {LATEST_PATH.name} and {HISTORY_PATH.name}", flush=True)


if __name__ == "__main__":
    main()

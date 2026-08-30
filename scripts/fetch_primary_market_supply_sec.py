
from pathlib import Path
from datetime import date, datetime
import io, os, re, time
import numpy as np
import pandas as pd
import requests

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"data"/"processed"
RAW=ROOT/"data"/"raw"
OUT.mkdir(parents=True,exist_ok=True)
RAW.mkdir(parents=True,exist_ok=True)

SEC_UA=os.environ.get(
    "SEC_USER_AGENT",
    "MarketLeadershipDashboard/1.0 (GitHub Actions research pipeline)"
)
HEADERS={
    "User-Agent":SEC_UA,
    "Accept-Encoding":"gzip, deflate",
    "Host":"www.sec.gov",
}
DATA_HEADERS={
    "User-Agent":SEC_UA,
    "Accept-Encoding":"gzip, deflate",
    "Host":"data.sec.gov",
}
CACHE=RAW/"sec_issuer_quality_cache.csv"

FORMS={"424B4","424B5","S-1","S-1/A"}
SPAC_RE=re.compile(r"\b(acquisition|blank check)\b",re.I)

def quarter(d):
    return (d.month-1)//3+1

def get_text(url,headers=HEADERS):
    r=requests.get(url,headers=headers,timeout=45)
    r.raise_for_status()
    return r.text

def parse_master(text):
    lines=text.splitlines()
    start=0
    for i,line in enumerate(lines):
        if line.startswith("CIK|Company Name|Form Type|Date Filed|Filename"):
            start=i+1; break
    rows=[]
    for line in lines[start:]:
        p=line.split("|")
        if len(p)!=5: continue
        cik,name,form,dt,fn=p
        if form not in FORMS: continue
        rows.append({
            "cik":str(cik).strip(),
            "company_name":name.strip(),
            "form":form.strip(),
            "date":pd.to_datetime(dt,errors="coerce"),
            "filename":fn.strip(),
        })
    return pd.DataFrame(rows)

def load_history(years=5):
    today=date.today()
    start_year=today.year-years
    pieces=[]
    for y in range(start_year,today.year+1):
        qmax=quarter(today) if y==today.year else 4
        for q in range(1,qmax+1):
            url=f"https://www.sec.gov/Archives/edgar/full-index/{y}/QTR{q}/master.idx"
            try:
                txt=get_text(url)
                part=parse_master(txt)
                if len(part): pieces.append(part)
                time.sleep(0.15)
            except Exception as e:
                print("WARN index",y,q,e)
    if not pieces:
        raise RuntimeError("No SEC quarterly indexes could be loaded")
    x=pd.concat(pieces,ignore_index=True)
    x=x[x["date"].notna()].copy()
    x=x[x["date"].dt.date<=today]
    return x

def latest_profitability(cik):
    url=f"https://data.sec.gov/api/xbrl/companyfacts/CIK{int(cik):010d}.json"
    try:
        data=requests.get(url,headers=DATA_HEADERS,timeout=30).json()
    except Exception:
        return None
    facts=data.get("facts",{})
    candidates=[]
    for taxonomy,concept in [
        ("us-gaap","NetIncomeLoss"),
        ("ifrs-full","ProfitLoss"),
        ("ifrs-full","ProfitLossAttributableToOwnersOfParent"),
    ]:
        units=facts.get(taxonomy,{}).get(concept,{}).get("units",{})
        for unit,arr in units.items():
            if unit not in {"USD","EUR","GBP","JPY","CNY","CAD","CHF","KRW"}:
                continue
            for r in arr:
                fp=str(r.get("fp",""))
                form=str(r.get("form",""))
                val=r.get("val")
                filed=r.get("filed")
                if val is None or not filed: continue
                if form in {"10-K","20-F","40-F"} or fp=="FY":
                    candidates.append((filed,float(val)))
    if not candidates:
        return None
    candidates.sort(key=lambda z:z[0])
    return candidates[-1][1] > 0

def issuer_quality(recent):
    if CACHE.exists():
        cache=pd.read_csv(CACHE,dtype={"cik":str})
    else:
        cache=pd.DataFrame(columns=["cik","profitable","checked_at"])

    known={str(r["cik"]):r for _,r in cache.iterrows()}
    out=[]
    candidates=recent.drop_duplicates("cik").head(60)
    for _,r in candidates.iterrows():
        cik=str(r["cik"])
        name=str(r["company_name"])
        spac=bool(SPAC_RE.search(name))
        prof=None
        if cik in known and pd.notna(known[cik].get("profitable")):
            raw=known[cik].get("profitable")
            prof=str(raw).lower() in {"true","1","yes"}
        elif not spac:
            try:
                prof=latest_profitability(cik)
                time.sleep(0.12)
            except Exception:
                prof=None
        low_quality=True if spac else (None if prof is None else not prof)
        out.append({"cik":cik,"company_name":name,"spac":spac,"profitable":prof,"low_quality":low_quality})

    fresh=pd.DataFrame(out)
    cache_new=fresh[["cik","profitable"]].copy()
    cache_new["checked_at"]=date.today().isoformat()
    cache_all=pd.concat([cache,cache_new],ignore_index=True)
    cache_all=cache_all.drop_duplicates("cik",keep="last")
    cache_all.to_csv(CACHE,index=False)
    return fresh

def main():
    filings=load_history(5)
    filings["month"]=filings["date"].dt.to_period("M").astype(str)
    filings["spac_proxy"]=filings["company_name"].str.contains(SPAC_RE,regex=True,na=False) & filings["form"].eq("424B4")

    hist=(
        filings.groupby("month")
        .agg(
            count_424b4=("form",lambda s:int((s=="424B4").sum())),
            count_424b5=("form",lambda s:int((s=="424B5").sum())),
            count_s1=("form",lambda s:int(s.isin(["S-1","S-1/A"]).sum())),
            count_spac_proxy=("spac_proxy","sum"),
            unique_issuers=("cik","nunique"),
        )
        .reset_index()
        .sort_values("month")
    )
    hist["primary_supply_events"]=hist["count_424b4"]+hist["count_424b5"]
    hist["supply_3m_avg"]=hist["primary_supply_events"].rolling(3,min_periods=1).mean()
    # Data-adaptive percentile: current supply relative to its own 5y distribution.
    latest_3m=float(hist["supply_3m_avg"].iloc[-1])
    dist=hist["supply_3m_avg"].dropna()
    percentile=float((dist<=latest_3m).mean()) if len(dist) else np.nan

    if percentile>=0.95:
        supply_state="frenzy"
    elif percentile>=0.80:
        supply_state="rising"
    elif percentile<=0.20:
        supply_state="subdued"
    else:
        supply_state="normal"

    cutoff=pd.Timestamp.today().normalize()-pd.Timedelta(days=92)
    recent=filings[(filings["date"]>=cutoff) & filings["form"].eq("424B4")].copy()
    quality=issuer_quality(recent)
    covered=quality["low_quality"].notna() if len(quality) else pd.Series(dtype=bool)
    coverage=float(covered.mean()) if len(quality) else 0.0
    low_share=float(quality.loc[covered,"low_quality"].astype(bool).mean()) if covered.any() else np.nan

    if coverage<0.40 or pd.isna(low_share):
        lq_state="unknown"
    elif low_share>=0.50:
        lq_state="high"
    elif low_share<=0.25:
        lq_state="low"
    else:
        lq_state="normal"

    last3=hist.tail(3)
    row={
        "as_of":str(filings["date"].max().date()),
        "ready":True,
        "supply_state":supply_state,
        "low_quality_state":lq_state,
        "ipo_proxy_424b4_3m":int(last3["count_424b4"].sum()),
        "followon_proxy_424b5_3m":int(last3["count_424b5"].sum()),
        "s1_registration_3m":int(last3["count_s1"].sum()),
        "spac_proxy_3m":int(last3["count_spac_proxy"].sum()),
        "supply_percentile_5y":percentile,
        "low_quality_share":low_share,
        "low_quality_coverage":coverage,
        "method_note":"SEC EDGAR proxy: 424B4 public-offering prospectus; 424B5 shelf/follow-on prospectus; S-1 registrations. SPAC proxy uses acquisition/blank-check names. Low-quality proxy = SPAC or latest annual net loss where SEC XBRL coverage exists.",
        "data_source":"SEC EDGAR full index + Companyfacts",
    }

    hist.to_csv(OUT/"primary_market_supply_history.csv",index=False)
    pd.DataFrame([row]).to_csv(OUT/"primary_market_supply_latest.csv",index=False)
    quality.to_csv(OUT/"primary_market_supply_recent_issuer_quality.csv",index=False)
    print(pd.DataFrame([row]).to_string(index=False))

if __name__=="__main__":
    main()

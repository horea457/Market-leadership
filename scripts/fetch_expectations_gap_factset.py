
from pathlib import Path
from datetime import datetime, timezone
import re
import pandas as pd
import requests
from lxml import html

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/"data"/"processed"
OUT.mkdir(parents=True, exist_ok=True)

TOPIC = "https://insight.factset.com/topic/earnings/page/1"
UA = "Mozilla/5.0 (compatible; MarketLeadershipDashboard/1.0)"

def get(url):
    r=requests.get(url,timeout=30,headers={"User-Agent":UA})
    r.raise_for_status()
    return r.text

def clean_text(doc):
    tree=html.fromstring(doc)
    return " ".join(tree.text_content().split())

def find_links(doc):
    tree=html.fromstring(doc)
    links=[]
    for a in tree.xpath("//a[@href]"):
        title=" ".join(a.text_content().split())
        href=a.get("href")
        if not title or not href:
            continue
        if href.startswith("/"):
            href="https://insight.factset.com"+href
        if href.startswith("https://insight.factset.com/"):
            links.append((title,href))
    # Preserve order, unique URLs.
    out=[]
    seen=set()
    for t,u in links:
        if u not in seen:
            seen.add(u); out.append((t,u))
    return out

def first_matching(links, predicates):
    for title,url in links:
        low=title.lower()
        if all(p(low) for p in predicates):
            return title,url
    return None,None

def pct(text, patterns):
    for pat in patterns:
        m=re.search(pat,text,re.I)
        if m:
            try: return float(m.group(1))
            except: pass
    return None

def date_from_text(text):
    m=re.search(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+20\d{2}",text)
    if not m: return None
    try: return datetime.strptime(m.group(0),"%B %d, %Y").date().isoformat()
    except: return None

def main():
    topic_doc=get(TOPIC)
    links=find_links(topic_doc)

    season_title,season_url=first_matching(
        links,[lambda s:"s&p 500 earnings season update" in s]
    )
    rev_title,rev_url=first_matching(
        links,[lambda s:"analyst" in s, lambda s:"eps estimate" in s]
    )

    if not season_url:
        raise RuntimeError("Latest FactSet Earnings Season Update link not found")
    season_text=clean_text(get(season_url))

    beat=pct(season_text,[
        r"(\d+(?:\.\d+)?)%\s+have reported actual EPS above estimates",
        r"(\d+(?:\.\d+)?)%\s+have reported actual EPS above the mean EPS estimate",
    ])
    surprise=pct(season_text,[
        r"reporting earnings that are\s+(\d+(?:\.\d+)?)%\s+above estimates",
        r"earnings surprise percentage.*?(\d+(?:\.\d+)?)%",
    ])
    ex_outlier=pct(season_text,[
        r"would fall to\s+(\d+(?:\.\d+)?)%\s+from",
        r"would be\s+(\d+(?:\.\d+)?)%\s+.*?excluding",
    ])
    fiveyr_beat=pct(season_text,[r"5-year average of\s+(\d+(?:\.\d+)?)%"])
    # The first 5-year average in a season update is normally the EPS beat-rate average.
    season_date=date_from_text(season_text)

    revision=None
    rev_date=None
    rev_text=""
    if rev_url:
        rev_text=clean_text(get(rev_url))
        rev_date=date_from_text(rev_text)
        up=re.search(r"(?:increased|increase).*?by\s+(\d+(?:\.\d+)?)%",rev_text,re.I)
        down=re.search(r"(?:decreased|declined|decrease).*?by\s+(\d+(?:\.\d+)?)%",rev_text,re.I)
        if up:
            revision=float(up.group(1))
        elif down:
            revision=-float(down.group(1))

    if beat is None and surprise is None and revision is None:
        raise RuntimeError("FactSet page was found but key metrics could not be parsed")

    # State is descriptive, not an optimized trading threshold.
    if revision is not None and revision > 0:
        expectation_state="rising"
    elif revision is not None and revision < 0:
        expectation_state="falling"
    else:
        expectation_state="neutral"

    surprise_ref = ex_outlier if ex_outlier is not None else surprise
    if beat is not None and fiveyr_beat is not None and beat > fiveyr_beat and (surprise_ref is None or surprise_ref > 0):
        surprise_state="positive"
    elif surprise_ref is not None and surprise_ref < 0:
        surprise_state="negative"
    else:
        surprise_state="neutral"

    as_of=max([d for d in [season_date,rev_date] if d], default=datetime.now(timezone.utc).date().isoformat())

    row={
        "as_of":as_of,
        "ready":True,
        "earnings_ready":True,
        "macro_ready":False,
        "expectation_state":expectation_state,
        "surprise_state":surprise_state,
        "eps_beat_rate":beat,
        "eps_beat_rate_5y_avg":fiveyr_beat,
        "eps_surprise_pct":surprise,
        "eps_surprise_pct_ex_outliers":ex_outlier,
        "eps_revision_pct":revision,
        "coverage":"S&P 500 earnings; macro consensus not included",
        "season_source_title":season_title,
        "season_source_url":season_url,
        "revision_source_title":rev_title,
        "revision_source_url":rev_url,
        "data_source":"FactSet Insight public earnings articles",
        "method_note":"Public aggregate earnings surprise and analyst estimate revision. Macro economic-surprise consensus is intentionally not inferred.",
    }
    pd.DataFrame([row]).to_csv(OUT/"expectations_gap_latest.csv",index=False)
    print(pd.DataFrame([row]).to_string(index=False))

if __name__=="__main__":
    main()

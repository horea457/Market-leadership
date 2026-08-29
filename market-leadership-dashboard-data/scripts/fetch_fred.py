from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

series = {
    "VIXCLS": "vix",
    "BAMLH0A0HYM2": "hy_oas",
}

frames = []
for sid, col in series.items():
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
    x = pd.read_csv(url)
    x.columns = ["date", col]
    x["date"] = pd.to_datetime(x["date"])
    x[col] = pd.to_numeric(x[col], errors="coerce")
    frames.append(x.set_index("date"))

df = pd.concat(frames, axis=1).sort_index()
df.to_csv(RAW / "fred_sentiment_proxies.csv", index_label="date")
print("FRED sentiment proxies updated.")

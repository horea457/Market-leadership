import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
steps = [
    ROOT / "scripts" / "fetch_prices.py",
    ROOT / "scripts" / "calc_leadership.py",
    ROOT / "scripts" / "fetch_breadth.py",
    ROOT / "scripts" / "fetch_stock_supply.py",
    ROOT / "scripts" / "fetch_fred.py",
    ROOT / "scripts" / "calc_sentiment.py",
]

for step in steps:
    if not step.exists():
        raise FileNotFoundError(f"Required pipeline step is missing: {step}")
    print(f"\n>>> {step.name}", flush=True)
    subprocess.run([sys.executable, str(step)], check=True)

print("\nAll data files updated.", flush=True)

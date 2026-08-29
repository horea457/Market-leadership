import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
steps = [
    ROOT / "scripts" / "fetch_prices.py",
    ROOT / "scripts" / "calc_leadership.py",
    ROOT / "scripts" / "fetch_breadth.py",
    ROOT / "scripts" / "fetch_fred.py",
    ROOT / "scripts" / "calc_sentiment.py",
]

for step in steps:
    print(f"\n>>> {step.name}")
    subprocess.run([sys.executable, str(step)], check=True)

print("\nAll data files updated.")


from pathlib import Path
import subprocess, sys

ROOT=Path(__file__).resolve().parent
SCRIPTS=[
    ROOT/"scripts"/"calc_sector_research_features.py",
    ROOT/"scripts"/"fetch_expectations_gap_factset.py",
    ROOT/"scripts"/"fetch_primary_market_supply_sec.py",
]

for s in SCRIPTS:
    print(f"\n=== V6.27 add-on: {s.name} ===")
    subprocess.run([sys.executable,str(s)],check=True)

print("\nV6.27 research add-ons completed.")

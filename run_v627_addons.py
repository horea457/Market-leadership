
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent

essential = [
    ROOT / "scripts" / "calc_sector_research_features.py",
]

optional = [
    ROOT / "scripts" / "fetch_expectations_gap_factset.py",
    ROOT / "scripts" / "fetch_primary_market_supply_sec.py",
]

for s in essential:
    print(f"\n=== V6.27 add-on (essential): {s.name} ===")
    subprocess.run([sys.executable, str(s)], check=True)

for s in optional:
    print(f"\n=== V6.27 add-on (optional/fail-soft): {s.name} ===")
    result = subprocess.run([sys.executable, str(s)], check=False)
    if result.returncode != 0:
        print(
            f"WARNING: {s.name} failed with exit code {result.returncode}. "
            "Continuing so other dashboard data can still update."
        )

print("\nV6.27 add-ons completed.")

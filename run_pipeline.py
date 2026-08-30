import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

REQUIRED = [
    ROOT / "scripts" / "fetch_prices.py",
    ROOT / "scripts" / "calc_leadership.py",
    ROOT / "scripts" / "calc_sector_research_features.py",
    ROOT / "scripts" / "fetch_breadth.py",
    ROOT / "scripts" / "fetch_stock_supply.py",
]

OPTIONAL_RESEARCH = [
    ROOT / "scripts" / "fetch_sector_fundamentals_sec.py",
    ROOT / "scripts" / "fetch_earnings_confirmation.py",
    ROOT / "scripts" / "fetch_primary_market_supply_sec.py",
]

TAIL_REQUIRED = [
    ROOT / "scripts" / "fetch_fred.py",
    ROOT / "scripts" / "calc_sentiment.py",
]

OPTIONAL_VALIDATION = [
    ROOT / "scripts" / "backtest_sector_research.py",
]


def run_required(step):
    if not step.exists():
        raise FileNotFoundError(f"Required pipeline step is missing: {step}")
    print(f"\n>>> REQUIRED: {step.name}", flush=True)
    subprocess.run([sys.executable, str(step)], check=True)


def run_optional(step):
    if not step.exists():
        print(f"\n>>> OPTIONAL missing, skipped: {step.name}", flush=True)
        return
    print(f"\n>>> OPTIONAL: {step.name}", flush=True)
    try:
        subprocess.run([sys.executable, str(step)], check=True)
    except subprocess.CalledProcessError as exc:
        # Research enrichments must not block the core weekly dashboard refresh.
        print(f"WARNING: optional step failed ({step.name}): {exc}", flush=True)


def main():
    for step in REQUIRED:
        run_required(step)

    # stock_supply detail is available at this point; SEC/earnings samplers can use it.
    for step in OPTIONAL_RESEARCH:
        run_optional(step)

    for step in TAIL_REQUIRED:
        run_required(step)

    # Long-history validation is cached for ~25 days inside the script.
    for step in OPTIONAL_VALIDATION:
        run_optional(step)

    print("\nAll core data updated; research enrichments attempted.", flush=True)


if __name__ == "__main__":
    main()

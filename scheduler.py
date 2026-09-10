"""Weekly entry point.

`python scheduler.py` runs the pipeline once and exits.
`python scheduler.py --serve` runs it once, then stays up for the weekly slot.

Collectors are isolated from each other: one failing source degrades the
digest rather than aborting the run.
"""

import argparse
import sys
import time
import traceback

import schedule

from analysis import digest, scorer
from collectors import endoflife, github, nvd, stackoverflow
from storage.db import init_db

COLLECTORS = [
    ("endoflife", endoflife),
    ("stackoverflow", stackoverflow),
    ("github", github),
    ("nvd", nvd),
]


def run_all() -> dict:
    init_db()
    summary = {"collectors": {}, "top": None, "digest": None}

    print("--- collectors ---")
    for name, module in COLLECTORS:
        try:
            summary["collectors"][name] = module.run()
        except Exception:
            summary["collectors"][name] = "failed"
            print(f"[{name}] FAILED — continuing with remaining sources")
            traceback.print_exc(limit=2)

    print("\n--- scoring ---")
    results = scorer.run()
    summary["top"] = results[0] if results else None
    for r in results[:5]:
        print(f"  {r['score']:5.0f}  {r['technology']:14} {r['triggers']}")

    print("\n--- digest ---")
    try:
        text = digest.generate_digest()
        summary["digest"] = "ok"
        print(text)
    except Exception as e:
        summary["digest"] = "failed"
        print(f"[digest] FAILED — {e}")

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="OpenLogic Trend Radar")
    parser.add_argument("--serve", action="store_true",
                        help="stay running and repeat every Monday at 07:00")
    args = parser.parse_args()

    summary = run_all()
    failed = [k for k, v in summary["collectors"].items() if v == "failed"]
    print(f"\nrun complete — collectors: {summary['collectors']}, "
          f"digest: {summary['digest']}")

    if args.serve:
        schedule.every().monday.at("07:00").do(run_all)
        print("scheduled: Mondays 07:00 — Ctrl+C to stop")
        while True:
            schedule.run_pending()
            time.sleep(60)

    return 1 if failed or summary["digest"] == "failed" else 0


if __name__ == "__main__":
    sys.exit(main())

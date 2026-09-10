"""endoflife.date collector — EOL dates per technology.

No auth required. Populates the eol_events table that the scorer depends on.

Response shape (validated against the live API):
  GET /api/{product}.json -> list of cycle objects
  cycle["eol"] is a date string ("2026-09-18") for most cycles, but a bool for
  some (nodejs cycle 3 -> True, meaning already EOL with no recorded date).
  Only date strings are usable, so bools are skipped.
"""

import requests

from config import OPENLOGIC_CATALOG, eol_slugs
from storage.db import insert_eol_event

BASE_URL = "https://endoflife.date/api"


def fetch_product(slug: str) -> list[dict] | None:
    """Cycle list for one endoflife.date product, or None if it has no data."""
    r = requests.get(f"{BASE_URL}/{slug}.json", timeout=15)
    if r.status_code != 200:
        print(f"[EOL]   ! no data for slug '{slug}' (HTTP {r.status_code})")
        return None
    return r.json()


def run() -> int:
    """Collect EOL cycles for every catalog technology. Returns rows written."""
    written = 0

    for tech in OPENLOGIC_CATALOG:
        slugs = eol_slugs(tech)
        if not slugs:
            print(f"[EOL] {tech}: no endoflife.date product — skipped")
            continue

        tech_rows = 0
        for slug in slugs:
            try:
                cycles = fetch_product(slug)
            except Exception as e:
                print(f"[EOL]   ! {tech}/{slug} request failed: {e}")
                continue
            if not cycles:
                continue

            for cycle in cycles:
                eol_date = cycle.get("eol")
                # bool means "supported"/"unsupported" with no date attached
                if not eol_date or isinstance(eol_date, bool):
                    continue

                # Namespace the version when a technology draws on more than one
                # product, so oracle-jdk 8 and redhat-build-of-openjdk 8 don't
                # collide on the (technology, version) unique index.
                cycle_id = str(cycle.get("cycle"))
                version = f"{slug}:{cycle_id}" if len(slugs) > 1 else cycle_id

                insert_eol_event(
                    technology=tech,
                    version=version,
                    eol_date=eol_date,
                    latest_version=cycle.get("latest"),
                    is_lts=bool(cycle.get("lts", False)),
                )
                tech_rows += 1

        written += tech_rows
        print(f"[EOL] {tech}: {tech_rows} cycles with dates")

    print(f"[EOL] done — {written} rows written")
    return written


if __name__ == "__main__":
    from storage.db import init_db
    init_db()
    run()

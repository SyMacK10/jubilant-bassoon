"""GitHub collector — migration/EOL issue chatter per technology.

Two corrections against the live API:

1. The search endpoint now rejects a query without `is:issue` or
   `is:pull-request` (HTTP 422). The reference query returned no data at all.
2. An unbounded count is not a signal. "tomcat (migrate OR ...)" matches
   185k issues all-time, and "java" matches ~88k in a month, so an absolute
   threshold fires for every technology. Counts are bounded to a 7-day window
   and compared week-over-week, matching the weekly cadence used elsewhere.

Search is rate limited to 30 requests/minute, and this makes 2 requests per
technology, so calls are throttled.
"""

import time
from datetime import date, timedelta

import requests

from config import API_KEYS, OPENLOGIC_CATALOG
from storage.db import insert_signal

SEARCH_URL = "https://api.github.com/search/issues"
HEADERS = {
    "Authorization": f"token {API_KEYS['github']}",
    "Accept": "application/vnd.github+json",
}
MIGRATION_KEYWORDS = ["migrate", "migration", "upgrade", "eol", "deprecated"]
THROTTLE_SECONDS = 2.2  # stays under the 30 req/min search limit


def _count(tech: str, start: date, end: date) -> int:
    """Issues mentioning the technology and a migration keyword in a window."""
    keywords = " OR ".join(MIGRATION_KEYWORDS)
    query = f"{tech} ({keywords}) is:issue created:{start.isoformat()}..{end.isoformat()}"

    r = requests.get(SEARCH_URL, headers=HEADERS,
                     params={"q": query, "per_page": 1}, timeout=25)

    # Secondary rate limit — back off once and retry.
    if r.status_code in (403, 429):
        wait = int(r.headers.get("retry-after", 60))
        print(f"[GH]   rate limited, waiting {wait}s")
        time.sleep(wait)
        r = requests.get(SEARCH_URL, headers=HEADERS,
                         params={"q": query, "per_page": 1}, timeout=25)

    r.raise_for_status()
    return r.json().get("total_count", 0)


def run() -> int:
    today = date.today()
    written = 0

    for tech in OPENLOGIC_CATALOG:
        try:
            current = _count(tech, today - timedelta(days=7), today)
            time.sleep(THROTTLE_SECONDS)
            prior = _count(tech, today - timedelta(days=14), today - timedelta(days=7))
            time.sleep(THROTTLE_SECONDS)
        except Exception as e:
            print(f"[GH] {tech}: request failed — {e}")
            continue

        delta_pct = ((current - prior) / max(prior, 1)) * 100

        insert_signal(
            source="github",
            technology=tech,
            metric="migration_issue_mentions",
            value=current,
            delta_pct=delta_pct,
            metadata={"prior_window": prior, "keywords": MIGRATION_KEYWORDS},
        )
        written += 1
        print(f"[GH] {tech:14} {current:6} issues (prior {prior:6})  {delta_pct:+7.1f}%")

    print(f"[GH] done — {written} signals written")
    return written


if __name__ == "__main__":
    from storage.db import init_db
    init_db()
    run()

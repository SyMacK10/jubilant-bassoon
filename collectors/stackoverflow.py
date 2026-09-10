"""Stack Overflow collector — week-over-week question volume delta.

Counts questions *created* in each window (sort=creation), not merely active,
so an old question receiving a new answer does not inflate the current week.

The prior-window count is stored in metadata because the delta alone is not
enough to judge a spike: post-2023 tag volumes are low enough that a swing of
a few questions reads as a large percentage move. The scorer applies a
minimum-volume floor using this value.
"""

import time
from datetime import datetime, timedelta, timezone

import requests

from config import API_KEYS, OPENLOGIC_CATALOG, so_tag
from storage.db import insert_signal

BASE_URL = "https://api.stackexchange.com/2.3"
THROTTLE_SECONDS = 0.3


def fetch_tag_volume(tag: str, start_days_ago: int, end_days_ago: int) -> int:
    """Count of questions created for a tag in a bounded window."""
    now = datetime.now(timezone.utc)
    params = {
        "key": API_KEYS["stackoverflow"],
        "site": "stackoverflow",
        "tagged": tag,
        "fromdate": int((now - timedelta(days=start_days_ago)).timestamp()),
        "todate": int((now - timedelta(days=end_days_ago)).timestamp()),
        "sort": "creation",
        "order": "desc",
        "filter": "total",
    }
    r = requests.get(f"{BASE_URL}/questions", params=params, timeout=20)
    r.raise_for_status()
    data = r.json()

    # The API asks callers to pause when it returns a backoff.
    if data.get("backoff"):
        time.sleep(data["backoff"] + 1)

    return data.get("total", 0)


def run() -> int:
    """Collect WoW question volume for every catalog technology."""
    written = 0

    for tech in OPENLOGIC_CATALOG:
        tag = so_tag(tech)
        try:
            current = fetch_tag_volume(tag, 7, 0)     # last 7 days
            time.sleep(THROTTLE_SECONDS)
            prior = fetch_tag_volume(tag, 14, 7)      # the 7 days before that
            time.sleep(THROTTLE_SECONDS)
        except Exception as e:
            print(f"[SO] {tech}: request failed — {e}")
            continue

        delta_pct = ((current - prior) / max(prior, 1)) * 100

        insert_signal(
            source="stackoverflow",
            technology=tech,
            metric="question_volume",
            value=current,
            delta_pct=delta_pct,
            metadata={"tag": tag, "prior_window": prior, "current_window": current},
        )
        written += 1
        print(f"[SO] {tech:14} {current:4} questions (prior {prior:4})  {delta_pct:+7.1f}%")

    print(f"[SO] done — {written} signals written")
    return written


if __name__ == "__main__":
    from storage.db import init_db
    init_db()
    run()

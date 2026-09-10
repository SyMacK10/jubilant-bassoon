"""Hacker News collector — end-of-life discussion among practitioners.

Uses the Algolia search backend, which needs no auth, no registration and
carries no commercial-use restriction.

Two things this source is not:
- It is not a volume signal. Measured yield is a handful of genuinely
  EOL-related posts per technology per six months, so the window is 180 days
  rather than the weekly window used elsewhere, and the scoring weight is
  small and floor-gated.
- It is not usable via relevance search alone. Filtering happens in
  _discussion.match after a broad retrieve.

Its real value is verbatim practitioner language for the digest.
"""

import time
from datetime import datetime, timedelta, timezone

import requests

from collectors import _discussion
from config import OPENLOGIC_CATALOG, discussion_tokens
from storage.db import insert_signal

SEARCH_URL = "https://hn.algolia.com/api/v1/search"
WINDOW_DAYS = 180
MAX_QUOTES = 3
THROTTLE_SECONDS = 0.4


def _search(term: str, days: int) -> list[dict]:
    cutoff = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp())
    r = requests.get(SEARCH_URL, params={
        "query": term,
        "tags": "(story,comment)",
        "hitsPerPage": 100,
        "numericFilters": f"created_at_i>{cutoff}",
    }, timeout=25)
    r.raise_for_status()
    return r.json().get("hits", [])


def run(days: int = WINDOW_DAYS) -> int:
    written = 0

    for tech in OPENLOGIC_CATALOG:
        tokens = discussion_tokens(tech)
        try:
            hits = _search(tech, days)
        except Exception as e:
            print(f"[HN] {tech}: request failed — {e}")
            continue
        finally:
            time.sleep(THROTTLE_SECONDS)

        quotes, seen = [], set()
        for hit in hits:
            text = _discussion.normalise(
                hit.get("title"), hit.get("story_title"), hit.get("comment_text"))
            ok, keyword = _discussion.match(text, tokens)
            if not ok or hit.get("objectID") in seen:
                continue
            seen.add(hit.get("objectID"))
            quotes.append({
                "text": _discussion.snippet(text, tokens),
                "keyword": keyword,
                "url": f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                "points": hit.get("points") or 0,
            })

        quotes.sort(key=lambda q: q["points"], reverse=True)
        insert_signal(
            source="hackernews",
            technology=tech,
            metric="eol_discussion",
            value=len(quotes),
            delta_pct=0,
            metadata={"window_days": days, "quotes": quotes[:MAX_QUOTES]},
        )
        written += 1
        print(f"[HN] {tech:14} {len(quotes):2} EOL discussions "
              f"(of {len(hits)} retrieved)")

    print(f"[HN] done — {written} signals written")
    return written


if __name__ == "__main__":
    from storage.db import init_db
    init_db()
    run()

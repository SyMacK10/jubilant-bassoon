"""Reddit collector — end-of-life discussion in practitioner subreddits.

DORMANT BY DEFAULT. Reddit's Responsible Builder Policy requires an approved
OAuth client, and commercial use (which this is — OpenLogic is a Perforce
product line and this drives marketing outreach) does not qualify for the
free non-commercial tier. This collector stays inert until
REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET are present in .env, so the
pipeline runs unaffected until access is granted.

Uses the official OAuth API only. The unauthenticated .json endpoints are
deliberately not used: those are exactly what the policy gates, and building
a commercial product on them would create real exposure.

NOTE: the request paths below follow Reddit's documented OAuth API but have
not been exercised against the live service, because no credentials exist
yet. Verify against a real response before trusting the parsing.
"""

import time

import requests

from collectors import _discussion
from config import (API_KEYS, OPENLOGIC_CATALOG, REDDIT_SUBREDDITS,
                    discussion_tokens)
from storage.db import insert_signal

TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
API_BASE = "https://oauth.reddit.com"
USER_AGENT = "python:openlogic-trend-radar:v0.1 (by /u/openlogic)"
MAX_QUOTES = 3
THROTTLE_SECONDS = 1.1  # free tier is ~100 queries/minute


def is_configured() -> bool:
    return bool(API_KEYS.get("reddit_client_id")
                and API_KEYS.get("reddit_client_secret"))


def _token() -> str:
    """App-only OAuth token via the client_credentials grant."""
    r = requests.post(
        TOKEN_URL,
        auth=(API_KEYS["reddit_client_id"], API_KEYS["reddit_client_secret"]),
        data={"grant_type": "client_credentials"},
        headers={"User-Agent": USER_AGENT},
        timeout=25,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def _search(token: str, subreddit: str, term: str) -> list[dict]:
    r = requests.get(
        f"{API_BASE}/r/{subreddit}/search",
        headers={"Authorization": f"bearer {token}", "User-Agent": USER_AGENT},
        params={"q": term, "restrict_sr": 1, "sort": "new",
                "t": "year", "limit": 100},
        timeout=25,
    )
    if r.status_code == 429:
        time.sleep(int(r.headers.get("retry-after", 30)))
        return []
    r.raise_for_status()
    return [c.get("data", {}) for c in r.json().get("data", {}).get("children", [])]


def run() -> int:
    if not is_configured():
        print("[RD] skipped — REDDIT_CLIENT_ID/REDDIT_CLIENT_SECRET not set. "
              "Reddit requires an approved OAuth client; commercial use needs "
              "a separate agreement.")
        return 0

    try:
        token = _token()
    except Exception as e:
        print(f"[RD] auth failed — {e}")
        return 0

    written = 0
    for tech in OPENLOGIC_CATALOG:
        tokens = discussion_tokens(tech)
        quotes, seen = [], set()

        for sub in REDDIT_SUBREDDITS:
            try:
                posts = _search(token, sub, f"{tech} end of life")
            except Exception as e:
                print(f"[RD] {tech}/r/{sub}: {e}")
                continue
            finally:
                time.sleep(THROTTLE_SECONDS)

            for post in posts:
                text = _discussion.normalise(post.get("title"),
                                             post.get("selftext"))
                ok, keyword = _discussion.match(text, tokens)
                pid = post.get("id")
                if not ok or pid in seen:
                    continue
                seen.add(pid)
                quotes.append({
                    "text": _discussion.snippet(text, tokens),
                    "keyword": keyword,
                    "url": "https://reddit.com" + (post.get("permalink") or ""),
                    "subreddit": sub,
                    "points": post.get("score") or 0,
                })

        quotes.sort(key=lambda q: q["points"], reverse=True)
        insert_signal(
            source="reddit",
            technology=tech,
            metric="eol_discussion",
            value=len(quotes),
            delta_pct=0,
            metadata={"quotes": quotes[:MAX_QUOTES],
                      "subreddits": REDDIT_SUBREDDITS},
        )
        written += 1
        print(f"[RD] {tech:14} {len(quotes):2} EOL discussions")

    print(f"[RD] done — {written} signals written")
    return written


if __name__ == "__main__":
    from storage.db import init_db
    init_db()
    run()

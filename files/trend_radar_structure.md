# OpenLogic Trend Radar — Project Structure

```
openlogic-trend-radar/
├── config.py                  # API keys, tech catalog, scoring thresholds
├── scheduler.py               # Runs all collectors on a weekly cron
├── requirements.txt
│
├── collectors/
│   ├── __init__.py
│   ├── stackoverflow.py       # Tag volume + week-over-week delta
│   ├── github.py              # Repo topics, issue keywords, release notes
│   ├── reddit.py              # r/devops, r/sysadmin, r/java keyword freq
│   ├── endoflife.py           # endoflife.date API — EOL dates by product
│   ├── nvd.py                 # NVD CVE feed filtered to catalog techs
│   └── package_stats.py       # npm, Maven Central, PyPI download trends
│
├── storage/
│   ├── __init__.py
│   ├── db.py                  # SQLite read/write helpers
│   └── schema.sql             # Tables: signals, technologies, eol_events, digests
│
├── analysis/
│   ├── __init__.py
│   ├── scorer.py              # Spike detection, EOL proximity weighting
│   ├── mapper.py              # Maps raw tech names to OpenLogic catalog
│   └── digest.py             # Sends scored signals to Claude API → summary
│
└── dashboard/
    ├── app.py                 # Streamlit app (or serves React build)
    └── components/            # Chart helpers if using Streamlit
```

---

## config.py

```python
# config.py

API_KEYS = {
    "stackoverflow": "YOUR_KEY",
    "github": "YOUR_KEY",
    "reddit_client_id": "YOUR_KEY",
    "reddit_secret": "YOUR_KEY",
    "anthropic": "YOUR_KEY",
    "nvd": "YOUR_KEY",  # optional but increases rate limit
}

# Technologies OpenLogic actively supports — used to filter all signals
OPENLOGIC_CATALOG = [
    "java", "python", "php", "ruby", "nodejs",
    "postgresql", "mysql", "mongodb",
    "kafka", "elasticsearch", "hadoop",
    "spring", "tomcat", "jboss", "wildfly",
    "centos", "rhel", "ubuntu",
    # Add more as needed
]

SCORING = {
    "eol_within_90_days": 30,
    "eol_within_180_days": 20,
    "stackoverflow_spike_30pct": 15,
    "github_migration_keyword": 10,
    "critical_cve": 25,
    "high_cve": 15,
}
```

---

## collectors/stackoverflow.py

```python
import requests
from datetime import datetime, timedelta
from config import API_KEYS, OPENLOGIC_CATALOG
from storage.db import insert_signal

BASE_URL = "https://api.stackexchange.com/2.3"

def fetch_tag_volume(tag: str, days_back: int = 7) -> int:
    """Returns question count for a tag in the past N days."""
    to_date = int(datetime.now().timestamp())
    from_date = int((datetime.now() - timedelta(days=days_back)).timestamp())
    
    params = {
        "key": API_KEYS["stackoverflow"],
        "site": "stackoverflow",
        "tagged": tag,
        "fromdate": from_date,
        "todate": to_date,
        "filter": "total",
    }
    r = requests.get(f"{BASE_URL}/questions", params=params)
    return r.json().get("total", 0)

def run():
    """Fetch volume for all catalog techs, compute delta, store signal."""
    for tech in OPENLOGIC_CATALOG:
        current = fetch_tag_volume(tech, days_back=7)
        prior = fetch_tag_volume(tech, days_back=14)  # prior 7-day window
        
        delta_pct = ((current - prior) / max(prior, 1)) * 100
        
        insert_signal(
            source="stackoverflow",
            technology=tech,
            metric="question_volume",
            value=current,
            delta_pct=delta_pct,
        )
        print(f"[SO] {tech}: {current} questions, {delta_pct:.1f}% delta")
```

---

## collectors/endoflife.py

```python
import requests
from storage.db import insert_eol_event
from config import OPENLOGIC_CATALOG

BASE_URL = "https://endoflife.date/api"

def run():
    """Pull EOL dates for all catalog technologies."""
    for tech in OPENLOGIC_CATALOG:
        try:
            r = requests.get(f"{BASE_URL}/{tech}.json")
            if r.status_code != 200:
                continue
            
            for cycle in r.json():
                eol_date = cycle.get("eol")
                if not eol_date or eol_date is True or eol_date is False:
                    continue
                
                insert_eol_event(
                    technology=tech,
                    version=cycle.get("cycle"),
                    eol_date=eol_date,
                    latest_version=cycle.get("latest"),
                    is_lts=cycle.get("lts", False),
                )
        except Exception as e:
            print(f"[EOL] Failed for {tech}: {e}")
```

---

## collectors/nvd.py

```python
import requests
from datetime import datetime, timedelta
from storage.db import insert_signal
from config import API_KEYS, OPENLOGIC_CATALOG

NVD_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"

def run():
    """Pull recent CVEs for catalog technologies."""
    pub_start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%dT00:00:00.000")
    pub_end = datetime.now().strftime("%Y-%m-%dT23:59:59.999")
    
    for tech in OPENLOGIC_CATALOG:
        params = {
            "keywordSearch": tech,
            "pubStartDate": pub_start,
            "pubEndDate": pub_end,
            "apiKey": API_KEYS.get("nvd"),
        }
        r = requests.get(NVD_URL, params=params)
        data = r.json()
        
        for vuln in data.get("vulnerabilities", []):
            cve = vuln.get("cve", {})
            severity = (
                cve.get("metrics", {})
                .get("cvssMetricV31", [{}])[0]
                .get("cvssData", {})
                .get("baseSeverity", "UNKNOWN")
            )
            insert_signal(
                source="nvd",
                technology=tech,
                metric="cve",
                value=1,
                delta_pct=0,
                metadata={"cve_id": cve.get("id"), "severity": severity},
            )
```

---

## collectors/github.py

```python
import requests
from storage.db import insert_signal
from config import API_KEYS, OPENLOGIC_CATALOG

HEADERS = {"Authorization": f"token {API_KEYS['github']}"}
MIGRATION_KEYWORDS = ["migrate", "migration", "upgrade", "eol", "end of life", "deprecated", "replace"]

def search_issues(tech: str) -> dict:
    """Search recent GitHub issues mentioning migration/EOL keywords for a tech."""
    keyword_query = " OR ".join(MIGRATION_KEYWORDS)
    query = f"{tech} ({keyword_query})"
    
    url = "https://api.github.com/search/issues"
    params = {"q": query, "sort": "created", "order": "desc", "per_page": 30}
    r = requests.get(url, headers=HEADERS, params=params)
    return r.json()

def run():
    for tech in OPENLOGIC_CATALOG:
        data = search_issues(tech)
        count = data.get("total_count", 0)
        
        insert_signal(
            source="github",
            technology=tech,
            metric="migration_issue_mentions",
            value=count,
            delta_pct=0,
        )
        print(f"[GH] {tech}: {count} migration-related issues")
```

---

## storage/schema.sql

```sql
CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,           -- 'stackoverflow', 'github', 'nvd', etc.
    technology TEXT NOT NULL,
    metric TEXT NOT NULL,
    value REAL,
    delta_pct REAL,
    metadata TEXT,                  -- JSON blob for extra fields
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS eol_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    technology TEXT NOT NULL,
    version TEXT,
    eol_date DATE,
    latest_version TEXT,
    is_lts BOOLEAN,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS scored_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    technology TEXT NOT NULL,
    total_score REAL,
    score_breakdown TEXT,           -- JSON
    trigger_type TEXT,              -- 'eol_proximity', 'demand_spike', 'cve', 'migration_signal'
    scored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS digests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    summary TEXT,
    top_technologies TEXT,          -- JSON array
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## analysis/scorer.py

```python
from datetime import datetime, date
from storage.db import get_signals, get_eol_events, insert_scored_signal
from config import SCORING

def score_technology(tech: str) -> dict:
    score = 0
    breakdown = {}
    trigger_types = []

    # --- EOL Proximity ---
    eol_events = get_eol_events(tech)
    for event in eol_events:
        eol = date.fromisoformat(event["eol_date"])
        days_until = (eol - date.today()).days
        if 0 < days_until <= 90:
            score += SCORING["eol_within_90_days"]
            breakdown["eol_90"] = days_until
            trigger_types.append("eol_proximity")
        elif 0 < days_until <= 180:
            score += SCORING["eol_within_180_days"]
            breakdown["eol_180"] = days_until
            trigger_types.append("eol_proximity")

    # --- Stack Overflow Spike ---
    so_signals = get_signals(tech, source="stackoverflow")
    for sig in so_signals:
        if sig["delta_pct"] >= 30:
            score += SCORING["stackoverflow_spike_30pct"]
            breakdown["so_spike"] = sig["delta_pct"]
            trigger_types.append("demand_spike")

    # --- CVE Signals ---
    cve_signals = get_signals(tech, source="nvd")
    for sig in cve_signals:
        meta = sig.get("metadata", {})
        if meta.get("severity") == "CRITICAL":
            score += SCORING["critical_cve"]
            trigger_types.append("cve")
        elif meta.get("severity") == "HIGH":
            score += SCORING["high_cve"]
            trigger_types.append("cve")

    # --- GitHub Migration Mentions ---
    gh_signals = get_signals(tech, source="github")
    for sig in gh_signals:
        if sig["value"] > 10:
            score += SCORING["github_migration_keyword"]
            breakdown["gh_mentions"] = sig["value"]
            trigger_types.append("migration_signal")

    insert_scored_signal(
        technology=tech,
        total_score=score,
        score_breakdown=breakdown,
        trigger_type=", ".join(set(trigger_types)),
    )
    return {"technology": tech, "score": score, "triggers": trigger_types}


def run():
    from config import OPENLOGIC_CATALOG
    results = [score_technology(t) for t in OPENLOGIC_CATALOG]
    return sorted(results, key=lambda x: x["score"], reverse=True)
```

---

## analysis/digest.py

```python
import anthropic
import json
from storage.db import get_top_scored_signals, get_eol_events
from config import API_KEYS

client = anthropic.Anthropic(api_key=API_KEYS["anthropic"])

def generate_digest(top_n: int = 10) -> str:
    top_signals = get_top_scored_signals(limit=top_n)
    
    # Build context payload for Claude
    context = []
    for sig in top_signals:
        eol_data = get_eol_events(sig["technology"])
        context.append({
            "technology": sig["technology"],
            "score": sig["total_score"],
            "triggers": sig["trigger_type"],
            "score_breakdown": json.loads(sig["score_breakdown"] or "{}"),
            "eol_events": eol_data[:3],  # limit to 3 nearest EOL dates
        })

    prompt = f"""
You are a market intelligence analyst for OpenLogic, a vendor that provides enterprise support 
for open source software. Your audience is the marketing team preparing outreach campaigns.

Below is a weekly signal report of technologies showing elevated activity:

{json.dumps(context, indent=2)}

Write a concise weekly digest (300-400 words) that:
1. Names the 3-5 highest priority technologies and explains WHY they are signals right now
2. Maps each to the likely buyer pain (e.g., "Java 8 EOL in 90 days = enterprises on extended support looking for a vendor")
3. Suggests one outreach angle or content topic per technology
4. Flags anything that looks like an emerging trend worth watching

Write in plain language. No bullet soup. Paragraph format. Treat this like a briefing memo.
"""

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    
    digest_text = message.content[0].text
    
    # Store digest
    from storage.db import insert_digest
    insert_digest(summary=digest_text, top_technologies=[s["technology"] for s in top_signals[:5]])
    
    return digest_text
```

---

## scheduler.py

```python
import schedule
import time
from collectors import stackoverflow, github, endoflife, nvd
from analysis import scorer, digest

def run_all():
    print("--- Running collectors ---")
    endoflife.run()
    stackoverflow.run()
    github.run()
    nvd.run()
    
    print("--- Scoring signals ---")
    results = scorer.run()
    print(f"Top signal: {results[0]}")
    
    print("--- Generating digest ---")
    summary = digest.generate_digest()
    print(summary)

# Run weekly on Monday mornings
schedule.every().monday.at("07:00").do(run_all)

if __name__ == "__main__":
    run_all()  # Run immediately on start
    while True:
        schedule.run_pending()
        time.sleep(60)
```

---

## requirements.txt

```
anthropic
requests
schedule
streamlit
plotly
sqlite3  # built-in
praw     # Reddit API wrapper
PyGithub # GitHub API wrapper (optional alternative to raw requests)
```

---

## API Keys You Will Need

| Source | Key Required | Where to Get It | Cost |
|---|---|---|---|
| Stack Overflow | Optional (higher rate limit) | stackapps.com | Free |
| GitHub | Yes | github.com/settings/tokens | Free |
| Reddit | Yes (Client ID + Secret) | reddit.com/prefs/apps | Free |
| NVD (NIST) | Optional (higher rate limit) | nvd.nist.gov/developers/request-an-api-key | Free |
| Anthropic | Yes | console.anthropic.com | Pay per use |
| endoflife.date | None | No key required | Free |

---

## Build Order (Recommended)

1. Set up SQLite schema + storage helpers
2. Build endoflife.py collector first (no auth, instant value)
3. Add Stack Overflow collector
4. Wire scorer.py with just those two sources
5. Add GitHub + NVD collectors
6. Build digest.py (Claude integration)
7. Build Streamlit dashboard on top of the DB
8. Add Reddit last (most complex auth)

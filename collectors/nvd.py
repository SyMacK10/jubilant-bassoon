"""NVD collector — recent CVEs affecting catalog technologies.

Three corrections against the live API:

1. Severity is read from a fallback chain, not cvssMetricV31 alone. NVD now
   publishes newer CVEs under cvssMetricV40; reading only V3.1 silently
   classified them UNKNOWN and they scored nothing.
2. Results are filtered by CPE. A keyword search for "tomcat" returns CVEs for
   unrelated products that merely mention it, so a CVE only counts when one of
   the technology's CPE tokens appears in its CPE list (handoff section 8,
   "NVD keyword noise"). CVEs with no CPE data yet fall back to a description
   check.
3. Multi-word keywords return nothing, so search terms are single tokens and
   precision comes from the CPE filter instead.

NVD asks for a 6 second gap between requests even with a key.
"""

import re
import time
from datetime import datetime, timedelta, timezone

import requests

from config import API_KEYS, OPENLOGIC_CATALOG, cpe_tokens, nvd_keyword
from storage.db import insert_signal

NVD_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
REQUEST_DELAY = 6  # seconds; mandated by NVD
DESCRIPTION_PREFIX_CHARS = 250
SEVERITY_KEYS = ("cvssMetricV40", "cvssMetricV31", "cvssMetricV30", "cvssMetricV2")


def _severity(cve: dict) -> str:
    """Highest-priority CVSS severity available, across metric versions."""
    metrics = cve.get("metrics", {})
    for key in SEVERITY_KEYS:
        entries = metrics.get(key) or []
        if not entries:
            continue
        data = entries[0].get("cvssData", {})
        sev = data.get("baseSeverity") or entries[0].get("baseSeverity")
        if sev:
            return sev.upper()
    return "UNKNOWN"


def _cpe_products(cve: dict) -> list[str]:
    """Vendor and product fields from each CPE URI.

    Parsed rather than substring-matched: a naive "java" in criteria also
    matches cpe:...:javascript:... and similar near-misses.
    """
    out = []
    for cfg in cve.get("configurations", []):
        for node in cfg.get("nodes", []):
            for match in node.get("cpeMatch", []):
                parts = match.get("criteria", "").lower().split(":")
                if len(parts) > 4:
                    out.extend([parts[3], parts[4]])  # vendor, product
    return out


def _description(cve: dict) -> str:
    for d in cve.get("descriptions", []):
        if d.get("lang") == "en":
            return d.get("value", "").lower()
    return ""


def _token_matches(token: str, field: str) -> bool:
    """True when the CPE vendor/product field really names this technology.

    Matches the whole field, or one underscore-separated component of it, so
    "java" matches java_se but not javascript.
    """
    return token == field or token in field.split("_")


def _is_relevant(cve: dict, tokens: list[str]) -> bool:
    """Keep a CVE only if it genuinely concerns this technology.

    CPE is authoritative but lags badly: only ~2-5% of CVEs under a week old
    carry CPE data, so requiring it would discard almost everything a weekly
    run sees. When CPE is absent, fall back to a word-boundary match against
    the opening of the description, where the affected product is named. The
    prefix window matters — unrelated advisories often mention a technology
    further down ("...deployed on Tomcat"), which a whole-description match
    would wrongly accept.
    """
    fields = _cpe_products(cve)
    if fields:
        return any(_token_matches(tok, f) for tok in tokens for f in fields)

    opening = _description(cve)[:DESCRIPTION_PREFIX_CHARS]
    return any(re.search(rf"\b{re.escape(tok)}\b", opening) for tok in tokens)


def run(days: int = 7) -> int:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    fmt = "%Y-%m-%dT%H:%M:%S.000"
    written = 0

    for tech in OPENLOGIC_CATALOG:
        params = {
            "keywordSearch": nvd_keyword(tech),
            "pubStartDate": start.strftime(fmt),
            "pubEndDate": end.strftime(fmt),
            "resultsPerPage": 200,
        }
        try:
            r = requests.get(NVD_URL, params=params,
                             headers={"apiKey": API_KEYS["nvd"]}, timeout=45)
            r.raise_for_status()
            vulns = r.json().get("vulnerabilities", [])
        except Exception as e:
            print(f"[NVD] {tech}: request failed — {e}")
            time.sleep(REQUEST_DELAY)
            continue

        tokens = cpe_tokens(tech)
        kept, dropped = 0, 0
        for v in vulns:
            cve = v.get("cve", {})
            if not _is_relevant(cve, tokens):
                dropped += 1
                continue
            insert_signal(
                source="nvd",
                technology=tech,
                metric="cve",
                value=1,
                delta_pct=0,
                metadata={"cve_id": cve.get("id"), "severity": _severity(cve)},
            )
            kept += 1
            written += 1

        print(f"[NVD] {tech:14} {kept:3} CVEs kept, {dropped:3} filtered out "
              f"(of {len(vulns)} returned)")
        time.sleep(REQUEST_DELAY)

    print(f"[NVD] done — {written} signals written")
    return written


if __name__ == "__main__":
    from storage.db import init_db
    init_db()
    run()

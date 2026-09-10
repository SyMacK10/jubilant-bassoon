"""Composite scoring — turns raw signals into a ranked buying-trigger list.

Two deliberate departures from the reference implementation:

1. EOL is scored once per technology, on the *nearest upcoming* cycle, not once
   per matching cycle. Scoring every cycle meant a technology tracked across
   more versions (or more distributions, like java) accumulated points as an
   artifact of catalog shape rather than real urgency. This settles the
   "version granularity" question in handoff section 8 in favour of scoring at
   the product level.

2. A demand spike additionally requires the prior window to clear a volume
   floor, because a percentage delta on single-digit question counts is noise.
"""

from datetime import date

from config import OPENLOGIC_CATALOG, SCORING, THRESHOLDS
from storage.db import (get_eol_events, get_signals, insert_scored_signal)


def _nearest_upcoming_eol(tech: str) -> tuple[int, dict] | tuple[None, None]:
    """Days until the soonest not-yet-passed EOL, and the cycle that owns it."""
    today = date.today()
    best = None
    for event in get_eol_events(tech):
        try:
            days = (date.fromisoformat(event["eol_date"]) - today).days
        except (ValueError, TypeError):
            continue
        if days > 0 and (best is None or days < best[0]):
            best = (days, event)
    return best if best else (None, None)


def score_technology(tech: str) -> dict:
    score = 0
    breakdown: dict = {}
    trigger_types: list[str] = []

    # --- EOL proximity (nearest upcoming cycle only) ---
    days_until, cycle = _nearest_upcoming_eol(tech)
    if days_until is not None:
        if days_until <= 90:
            score += SCORING["eol_within_90_days"]
            breakdown["eol_90"] = {"days": days_until, "version": cycle["version"]}
            trigger_types.append("eol_proximity")
        elif days_until <= 180:
            score += SCORING["eol_within_180_days"]
            breakdown["eol_180"] = {"days": days_until, "version": cycle["version"]}
            trigger_types.append("eol_proximity")

    # --- Demand spike (volume-gated) ---
    for sig in get_signals(tech, source="stackoverflow"):
        delta = sig.get("delta_pct") or 0
        prior = (sig.get("metadata") or {}).get("prior_window", 0)
        if delta >= THRESHOLDS["so_spike_pct"] and prior >= THRESHOLDS["so_min_prior_volume"]:
            score += SCORING["stackoverflow_spike_30pct"]
            breakdown["so_spike"] = {"delta_pct": round(delta, 1), "prior": prior}
            trigger_types.append("demand_spike")
        break  # most recent signal only

    # --- CVEs ---
    cve_counts = {"CRITICAL": 0, "HIGH": 0}
    for sig in get_signals(tech, source="nvd"):
        severity = (sig.get("metadata") or {}).get("severity")
        if severity == "CRITICAL":
            score += SCORING["critical_cve"]
            cve_counts["CRITICAL"] += 1
        elif severity == "HIGH":
            score += SCORING["high_cve"]
            cve_counts["HIGH"] += 1
    if cve_counts["CRITICAL"] or cve_counts["HIGH"]:
        breakdown["cves"] = cve_counts
        trigger_types.append("cve")

    # --- Migration chatter ---
    for sig in get_signals(tech, source="github"):
        if (sig.get("value") or 0) > THRESHOLDS["github_mentions"]:
            score += SCORING["github_migration_keyword"]
            breakdown["gh_mentions"] = sig["value"]
            trigger_types.append("migration_signal")
        break

    insert_scored_signal(
        technology=tech,
        total_score=score,
        score_breakdown=breakdown,
        trigger_type=", ".join(sorted(set(trigger_types))),
    )
    return {"technology": tech, "score": score, "triggers": trigger_types,
            "breakdown": breakdown}


def run() -> list[dict]:
    results = [score_technology(t) for t in OPENLOGIC_CATALOG]
    return sorted(results, key=lambda x: (-x["score"], x["technology"]))


if __name__ == "__main__":
    for r in run():
        print(f"  {r['score']:5.0f}  {r['technology']:14} {r['triggers']}")

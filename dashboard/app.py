"""Streamlit dashboard over the trend radar database.

Mirrors the information architecture of the React mockup in files/: a scored
signal table with trigger badges, a per-technology detail panel, and a tab for
the Claude digest. Read-only — it never runs collectors.
"""

import sys
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storage import db  # noqa: E402

st.set_page_config(page_title="OpenLogic Trend Radar", page_icon="📡",
                   layout="wide")

TRIGGER_LABELS = {
    "eol_proximity": "EOL",
    "demand_spike": "DEMAND",
    "cve": "CVE",
    "migration_signal": "MIGRATION",
}


def severity(score: float) -> str:
    if score >= 60:
        return "🔴 Critical"
    if score >= 40:
        return "🟠 High"
    if score >= 20:
        return "🟡 Watch"
    return "⚪ Quiet"


@st.cache_data(ttl=60)
def load() -> tuple[pd.DataFrame, dict, list]:
    scored = db.get_top_scored_signals(limit=100)
    rows, details = [], {}
    today = date.today()

    for s in scored:
        tech = s["technology"]
        breakdown = s.get("score_breakdown") or {}
        cves = breakdown.get("cves", {})
        eol_info = breakdown.get("eol_90") or breakdown.get("eol_180") or {}

        upcoming = [e for e in db.get_eol_events(tech)
                    if e["eol_date"] and e["eol_date"] >= today.isoformat()]
        sources = sorted({sig["source"] for sig in db.get_signals(tech)})

        rows.append({
            "Technology": tech,
            "Score": s["total_score"] or 0,
            "Severity": severity(s["total_score"] or 0),
            "Triggers": " ".join(
                TRIGGER_LABELS.get(t.strip(), t.strip())
                for t in (s["trigger_type"] or "").split(",") if t.strip()
            ) or "—",
            "EOL Days": eol_info.get("days"),
            "CVEs": (cves.get("CRITICAL", 0) + cves.get("HIGH", 0)) or None,
            "Sources": len(sources),
        })
        details[tech] = {"breakdown": breakdown, "upcoming": upcoming,
                         "sources": sources,
                         "signals": db.get_signals(tech)}

    digests = []
    with db.connect() as conn:
        digests = [dict(r) for r in conn.execute(
            "SELECT * FROM digests ORDER BY generated_at DESC LIMIT 10")]

    return pd.DataFrame(rows), details, digests


def main() -> None:
    if not db.DB_PATH.exists():
        st.error("No database yet. Run `python scheduler.py` first.")
        return

    df, details, digests = load()
    if df.empty:
        st.warning("No scored signals yet. Run `python scheduler.py`.")
        return

    st.title("📡 OpenLogic Trend Radar")
    active = df[df["Score"] > 0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Technologies tracked", len(df))
    c2.metric("Active signals", len(active))
    c3.metric("Top score", f"{df['Score'].max():.0f}")
    c4.metric("Last digest",
              digests[0]["generated_at"][:10] if digests else "—")

    tab_signals, tab_digest = st.tabs(["Signals", "Digest"])

    with tab_signals:
        only_active = st.checkbox("Show only technologies with a signal",
                                  value=True)
        view = active if only_active else df
        st.dataframe(
            view,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Score": st.column_config.ProgressColumn(
                    "Score", min_value=0,
                    max_value=float(max(df["Score"].max(), 1)), format="%.0f"),
                "EOL Days": st.column_config.NumberColumn(
                    "EOL Days", help="Days until the nearest upcoming EOL"),
                "CVEs": st.column_config.NumberColumn(
                    "CVEs", help="Critical + high CVEs this week"),
            },
        )

        st.subheader("Detail")
        tech = st.selectbox("Technology", view["Technology"].tolist())
        if tech:
            d = details[tech]
            left, right = st.columns(2)
            with left:
                st.markdown("**Score breakdown**")
                st.json(d["breakdown"] or {"note": "no triggers fired"})
                st.markdown(f"**Sources reporting:** {', '.join(d['sources']) or '—'}")
            with right:
                st.markdown("**Upcoming end of life**")
                if d["upcoming"]:
                    st.dataframe(pd.DataFrame([
                        {"Version": e["version"], "EOL": e["eol_date"],
                         "LTS": bool(e["is_lts"])} for e in d["upcoming"][:8]
                    ]), hide_index=True, use_container_width=True)
                else:
                    st.caption("No upcoming EOL data for this technology.")

            st.markdown("**Raw signals (latest run)**")
            st.dataframe(pd.DataFrame([
                {"Source": s["source"], "Metric": s["metric"],
                 "Value": s["value"], "Δ%": round(s["delta_pct"] or 0, 1),
                 "Collected": s["collected_at"]}
                for s in d["signals"]
            ]) if d["signals"] else pd.DataFrame([{"": "none"}]),
                hide_index=True, use_container_width=True)

    with tab_digest:
        if not digests:
            st.info("No digest generated yet.")
        else:
            pick = st.selectbox("Digest", [d["generated_at"] for d in digests])
            chosen = next(d for d in digests if d["generated_at"] == pick)
            st.markdown(chosen["summary"] or "_empty_")


if __name__ == "__main__":
    main()

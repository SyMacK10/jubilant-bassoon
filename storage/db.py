"""SQLite helpers for the trend radar.

`metadata`, `score_breakdown` and `top_technologies` are stored as JSON text
and transparently serialized on write / deserialized on read.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

DB_PATH = Path(__file__).resolve().parent.parent / "trend_radar.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

# Rows inserted within this many hours of a source's newest row are treated as
# belonging to the same collection run. Prevents scores compounding across runs
# (see handoff section 8, "Signal duplication").
RUN_WINDOW_HOURS = 6


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables and indexes. Idempotent."""
    with connect() as conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))


def _rows(cursor: Iterable[sqlite3.Row], json_fields: tuple[str, ...] = ()) -> list[dict]:
    """sqlite3.Row -> plain dict, decoding the named JSON columns."""
    out = []
    for row in cursor:
        d = dict(row)
        for field in json_fields:
            raw = d.get(field)
            if isinstance(raw, str) and raw:
                try:
                    d[field] = json.loads(raw)
                except json.JSONDecodeError:
                    pass  # leave the raw string rather than losing the value
        out.append(d)
    return out


# --------------------------------------------------------------------------
# writes
# --------------------------------------------------------------------------

def insert_signal(
    source: str,
    technology: str,
    metric: str,
    value: float | None = None,
    delta_pct: float | None = None,
    metadata: dict[str, Any] | None = None,
) -> int:
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO signals (source, technology, metric, value, delta_pct, metadata)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (source, technology, metric, value, delta_pct,
             json.dumps(metadata) if metadata is not None else None),
        )
        return cur.lastrowid


def insert_eol_event(
    technology: str,
    version: str,
    eol_date: str,
    latest_version: str | None = None,
    is_lts: bool = False,
) -> int:
    """Upsert on (technology, version) so weekly re-collection updates in place."""
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO eol_events (technology, version, eol_date, latest_version, is_lts)"
            " VALUES (?, ?, ?, ?, ?)"
            " ON CONFLICT(technology, version) DO UPDATE SET"
            "   eol_date=excluded.eol_date,"
            "   latest_version=excluded.latest_version,"
            "   is_lts=excluded.is_lts,"
            "   collected_at=CURRENT_TIMESTAMP",
            (technology, version, eol_date, latest_version, int(bool(is_lts))),
        )
        return cur.lastrowid


def insert_scored_signal(
    technology: str,
    total_score: float,
    score_breakdown: dict[str, Any] | None = None,
    trigger_type: str = "",
) -> int:
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO scored_signals (technology, total_score, score_breakdown, trigger_type)"
            " VALUES (?, ?, ?, ?)",
            (technology, total_score, json.dumps(score_breakdown or {}), trigger_type),
        )
        return cur.lastrowid


def insert_digest(summary: str, top_technologies: list[str] | None = None) -> int:
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO digests (summary, top_technologies) VALUES (?, ?)",
            (summary, json.dumps(top_technologies or [])),
        )
        return cur.lastrowid


# --------------------------------------------------------------------------
# reads
# --------------------------------------------------------------------------

def get_signals(technology: str, source: str | None = None,
                latest_run_only: bool = True) -> list[dict]:
    """Signals for a technology, by default only from each source's most recent run."""
    sql = "SELECT * FROM signals WHERE technology = ?"
    params: list[Any] = [technology]
    if source:
        sql += " AND source = ?"
        params.append(source)
    if latest_run_only:
        sub = ("SELECT MAX(collected_at) FROM signals WHERE technology = ?"
               + (" AND source = ?" if source else ""))
        sql += (f" AND collected_at >= datetime((({sub})), '-{RUN_WINDOW_HOURS} hours')")
        params.append(technology)
        if source:
            params.append(source)
    sql += " ORDER BY collected_at DESC"
    with connect() as conn:
        return _rows(conn.execute(sql, params), json_fields=("metadata",))


def get_eol_events(technology: str) -> list[dict]:
    """EOL cycles for a technology, soonest upcoming first."""
    with connect() as conn:
        return _rows(conn.execute(
            "SELECT * FROM eol_events WHERE technology = ?"
            " AND eol_date IS NOT NULL ORDER BY eol_date ASC",
            (technology,),
        ))


def get_top_scored_signals(limit: int = 10) -> list[dict]:
    """Highest-scoring technologies from the most recent scoring run."""
    with connect() as conn:
        return _rows(conn.execute(
            "SELECT * FROM scored_signals"
            " WHERE scored_at >= datetime((SELECT MAX(scored_at) FROM scored_signals),"
            f"                            '-{RUN_WINDOW_HOURS} hours')"
            " ORDER BY total_score DESC, technology ASC LIMIT ?",
            (limit,),
        ), json_fields=("score_breakdown",))

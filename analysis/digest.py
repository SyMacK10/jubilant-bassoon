"""Scored signals -> Claude API -> prose briefing for the marketing team."""

import json
from datetime import date

import anthropic

from config import API_KEYS
from storage.db import get_eol_events, get_top_scored_signals, insert_digest

MODEL = "claude-opus-5"


def _client() -> anthropic.Anthropic:
    """Built on demand so importing this module doesn't require a key."""
    if not API_KEYS.get("anthropic"):
        raise RuntimeError("ANTHROPIC_KEY is not set in .env")
    return anthropic.Anthropic(api_key=API_KEYS["anthropic"])


def _extract_text(message) -> str:
    """Concatenate text blocks.

    Not message.content[0].text — with thinking enabled the first block is a
    thinking block, so indexing position 0 returns the wrong block or raises.
    """
    return "".join(b.text for b in message.content if b.type == "text").strip()


def build_context(top_n: int = 10) -> list[dict]:
    """The scored picture handed to the model, newest scoring run only."""
    context = []
    for sig in get_top_scored_signals(limit=top_n):
        if not sig.get("total_score"):
            continue  # a zero score is not a signal worth briefing on
        # Only cycles that have not already passed. get_eol_events returns
        # every recorded cycle oldest-first, so unfiltered this handed the
        # model 1996-era dates under the heading "upcoming".
        today = date.today().isoformat()
        eol = [e for e in get_eol_events(sig["technology"])
               if e["eol_date"] and e["eol_date"] >= today][:3]
        context.append({
            "technology": sig["technology"],
            "score": sig["total_score"],
            "triggers": sig["trigger_type"],
            "score_breakdown": sig.get("score_breakdown") or {},
            "upcoming_eol": [
                {"version": e["version"], "eol_date": e["eol_date"]} for e in eol
            ],
        })
    return context


def generate_digest(top_n: int = 10) -> str:
    context = build_context(top_n)
    if not context:
        raise RuntimeError("No scored signals to brief on — run the collectors "
                           "and scorer first.")

    prompt = f"""
You are a market intelligence analyst for OpenLogic, a vendor providing enterprise
support for open source software. Your audience is the marketing team preparing
outreach campaigns.

Weekly signal report:

{json.dumps(context, indent=2, default=str)}

Write a concise weekly digest (300-400 words) that:
1. Names the 3-5 highest priority technologies and explains WHY they are signals now
2. Maps each to the likely buyer pain
3. Suggests one outreach angle or content topic per technology
4. Flags anything that looks like an emerging trend worth watching

Plain language. Paragraph format, not bullets. Write it like a briefing memo.
Do not invent data that is not in the signal report above.
"""

    message = _client().messages.create(
        model=MODEL,
        max_tokens=8000,
        thinking={"type": "adaptive"},
        output_config={"effort": "medium"},
        messages=[{"role": "user", "content": prompt}],
    )

    if message.stop_reason == "refusal":
        raise RuntimeError(f"Model declined: {message.stop_details}")

    digest_text = _extract_text(message)
    insert_digest(
        summary=digest_text,
        top_technologies=[c["technology"] for c in context[:5]],
    )
    return digest_text


if __name__ == "__main__":
    print(generate_digest())

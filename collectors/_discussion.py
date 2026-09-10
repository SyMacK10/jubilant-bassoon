"""Shared relevance filtering for free-text discussion sources.

Both discussion collectors retrieve broadly and filter precisely here, the
same shape as the NVD collector. Raw relevance search is not usable on its
own: searching Hacker News for "postgresql end of life" returns "Ask HN: Who
wants to be hired?", because the backend OR-matches the terms.
"""

import html
import re

from config import EOL_DISCUSSION_KEYWORDS

# Max characters allowed between the technology name and the lifecycle phrase —
# roughly one sentence, so the two have to be part of the same statement.
# Without this, any long thread that mentions a technology anywhere and the
# word "unsupported" anywhere else matches. Calibrated against a small sample
# (genuine EOL quotes measured 25-51 chars apart, a false positive 119), so
# revisit once there is more collected data.
PROXIMITY_CHARS = 80
SNIPPET_CHARS = 240


def normalise(*parts: str | None) -> str:
    """Join text fields into one lowercase, plain-text string.

    Comment bodies arrive as HTML fragments, so tags are stripped and entities
    decoded — otherwise quotes reach the digest carrying <p> and &gt; markup.
    """
    joined = " ".join(p for p in parts if p)
    joined = re.sub(r"<[^>]+>", " ", joined)
    joined = html.unescape(joined)
    return re.sub(r"\s+", " ", joined).strip().lower()


def match(text: str, tokens: list[str]) -> tuple[bool, str | None]:
    """True when the text is genuinely about this technology's EOL.

    Requires a whole-word technology match AND a support-lifecycle phrase
    within PROXIMITY_CHARS of it. Bare "migrate"/"upgrade" are excluded from
    the keyword list upstream because they matched schema-migration tooling
    and language rewrites rather than EOL pressure.
    """
    for token in tokens:
        found = re.search(r"\b" + re.escape(token) + r"\b", text)
        if not found:
            continue
        for keyword in EOL_DISCUSSION_KEYWORDS:
            at = text.find(keyword)
            if at >= 0 and abs(found.start() - at) <= PROXIMITY_CHARS:
                return True, keyword
    return False, None


def snippet(text: str, tokens: list[str]) -> str:
    """A short excerpt centred on the technology mention, for quoting."""
    centre = 0
    for token in tokens:
        found = re.search(r"\b" + re.escape(token) + r"\b", text)
        if found:
            centre = found.start()
            break
    start = max(0, centre - SNIPPET_CHARS // 3)
    out = text[start:start + SNIPPET_CHARS].strip()
    return ("…" if start > 0 else "") + out + ("…" if len(text) > start + SNIPPET_CHARS else "")

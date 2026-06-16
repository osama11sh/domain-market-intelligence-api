"""Independent trend-detection system.

Google Trends (via pytrends, see trends.py) is treated as one *optional* signal
that gets blended in when available. The baseline signal here works without it:
a curated category/keyword weight table plus a deterministic, time-shifting
"momentum" factor (hash of keyword + ISO week) so scores are stable within a
day but move over time without calling any external API.

This module also derives Heat Index, geographic breakdown, and expected
monthly clicks - all rule-based, all free-tier friendly.
"""

import datetime
import hashlib

# Baseline relative "buzz" for generic brand-relevant tokens (independent of niche).
_BUZZWORD_WEIGHTS: dict[str, int] = {
    "ai": 92, "app": 70, "hub": 55, "pro": 60, "go": 50, "plus": 45, "io": 65,
    "lab": 58, "co": 48, "now": 52, "ly": 50, "tech": 75, "cloud": 68, "data": 70,
}

# Per-category baseline trend level (0-100) used when no other signal matches.
_CATEGORY_BASELINE: dict[str, int] = {
    "fitness": 64, "crypto": 58, "pets": 60, "tech": 78, "food": 62, "travel": 55,
    "finance": 60, "fashion": 57, "gaming": 72, "beauty": 59, "generic": 50,
}

# Top markets per category as relative interest weights (sum ~100, "Other" implied).
_GEO_WEIGHTS: dict[str, dict[str, int]] = {
    "fitness": {"US": 34, "GB": 14, "AU": 12, "CA": 10, "DE": 8},
    "crypto": {"US": 30, "SG": 14, "DE": 11, "GB": 10, "IN": 9},
    "pets": {"US": 36, "GB": 13, "CA": 11, "AU": 10, "DE": 7},
    "tech": {"US": 38, "IN": 13, "GB": 10, "DE": 9, "CA": 8},
    "food": {"US": 32, "GB": 12, "IT": 10, "FR": 9, "CA": 8},
    "travel": {"US": 26, "GB": 13, "AU": 11, "DE": 10, "FR": 9},
    "finance": {"US": 35, "GB": 14, "SG": 10, "DE": 9, "CA": 8},
    "fashion": {"US": 28, "GB": 13, "FR": 12, "IT": 10, "BR": 9},
    "gaming": {"US": 30, "GB": 11, "DE": 10, "JP": 10, "BR": 9},
    "beauty": {"US": 29, "GB": 12, "FR": 11, "KR": 10, "BR": 9},
    "generic": {"US": 33, "GB": 13, "CA": 10, "AU": 9, "DE": 8},
}

_COUNTRY_NAMES = {
    "US": "United States", "GB": "United Kingdom", "CA": "Canada", "AU": "Australia",
    "DE": "Germany", "FR": "France", "IT": "Italy", "ES": "Spain", "BR": "Brazil",
    "MX": "Mexico", "IN": "India", "JP": "Japan", "NL": "Netherlands", "SE": "Sweden",
    "SG": "Singapore", "KR": "South Korea",
}


def _clamp(v: float, lo: int = 0, hi: int = 100) -> int:
    return max(lo, min(hi, round(v)))


def category_for_niche(niche: str) -> str:
    return niche.lower().strip() if niche.lower().strip() in _CATEGORY_BASELINE else "generic"


def _momentum(token: str) -> int:
    """Deterministic pseudo-variability that shifts weekly, no external call needed."""
    iso_week = datetime.date.today().isocalendar()[1]
    digest = hashlib.sha256(f"{token}-{iso_week}".encode()).hexdigest()
    return (int(digest[:4], 16) % 31) - 15  # -15..+15


def base_trend_score(token: str, category: str, pytrends_score: int | None = None) -> int:
    """Independent trend score (1-100) for a single keyword/token.

    The category baseline is the anchor (a niche's "natural" trend level);
    a recognized buzzword nudges it toward the buzzword's own weight rather
    than diluting it, so unrecognized tokens still land near their category's
    baseline instead of being dragged toward zero.
    """
    baseline = _CATEGORY_BASELINE.get(category, _CATEGORY_BASELINE["generic"])
    buzz = _BUZZWORD_WEIGHTS.get(token.lower())
    if buzz is not None:
        heuristic = _clamp(baseline + (buzz - baseline) * 0.4 + _momentum(token))
    else:
        heuristic = _clamp(baseline + _momentum(token))

    if pytrends_score is not None:
        # Real signal available: weight it higher than the heuristic baseline.
        return _clamp(pytrends_score * 0.65 + heuristic * 0.35)
    return max(1, heuristic)


def domain_trend_score(name: str, keywords: list[str], category: str,
                        pytrends_scores: dict[str, int] | None = None) -> int:
    """Trend score for a full domain name: max of its constituent keyword matches."""
    pytrends_scores = pytrends_scores or {}
    matched = [kw for kw in keywords if kw in name or name in kw]
    if not matched:
        return base_trend_score(name[:6], category)
    return max(base_trend_score(kw, category, pytrends_scores.get(kw)) for kw in matched)


def heat_index(trend_score: int, available_count: int, checked_count: int) -> int:
    """Blend trend score with scarcity (fewer available extensions => hotter)."""
    if checked_count == 0:
        scarcity = 0
    else:
        scarcity = _clamp(100 - (available_count / checked_count * 100))
    return _clamp(trend_score * 0.7 + scarcity * 0.3)


def geo_breakdown(category: str, trend_location: str = "auto") -> dict[str, int]:
    """Return country -> relative interest %. trend_location: auto|global|<ISO country>."""
    weights = _GEO_WEIGHTS.get(category, _GEO_WEIGHTS["generic"])

    loc = (trend_location or "auto").strip()
    loc_upper = loc.upper()
    if loc_upper in _COUNTRY_NAMES:
        return {_COUNTRY_NAMES[loc_upper]: 100}

    if loc.lower() == "global":
        # Flatten toward an even split across the known top markets + Other.
        n = len(weights) + 1
        even = round(100 / n)
        result = {_COUNTRY_NAMES.get(c, c): even for c in weights}
        result["Other"] = max(0, 100 - even * len(weights))
        return result

    # auto: use the category's natural top-market distribution as-is.
    result = {_COUNTRY_NAMES.get(c, c): w for c, w in weights.items()}
    accounted = sum(weights.values())
    result["Other"] = max(0, 100 - accounted)
    return result


def expected_monthly_clicks(heat: int, trend_score: int, total_score: int, category: str) -> int:
    """Rule-based estimate of organic clicks/month for a brand-new, unranked domain."""
    base_volume = {
        "fitness": 8000, "crypto": 12000, "pets": 6000, "tech": 15000, "food": 7000,
        "travel": 9000, "finance": 11000, "fashion": 6500, "gaming": 13000, "beauty": 7000,
        "generic": 5000,
    }.get(category, 5000)

    # New, un-indexed domains capture a tiny sliver of category search volume,
    # scaled up by how "hot" and well-scored the name is.
    share = (heat / 100) * (trend_score / 100) * (total_score / 100) * 0.006
    return max(5, round(base_volume * share))

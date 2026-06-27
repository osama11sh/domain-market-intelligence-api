"""Step 1 - Trend keyword fetch via pytrends with graceful fallback.

Produces two independent streams:
  Stream A (brandable): abstract/evocative terms suited for creative name construction
  Stream B (meaningful): literal niche keywords that make direct, descriptive domains
"""

import logging
from pytrends.request import TrendReq

logger = logging.getLogger(__name__)

# Literal niche keywords for meaningful Stream B fallback
_NICHE_SEEDS: dict[str, list[str]] = {
    "fitness": ["gym", "workout", "strength", "cardio", "yoga", "run", "train", "fit", "health", "muscle"],
    "crypto": ["bitcoin", "token", "defi", "wallet", "chain", "nft", "web3", "coin", "stake", "ledger"],
    "pets": ["dog", "cat", "puppy", "paw", "fetch", "fur", "pet", "bark", "meow", "vet"],
    "tech": ["app", "code", "cloud", "data", "ai", "dev", "stack", "net", "hub", "lab"],
    "food": ["eat", "cook", "chef", "fresh", "taste", "bite", "meal", "yum", "dish", "spice"],
    "travel": ["trip", "fly", "roam", "tour", "trek", "go", "voyage", "jet", "globe", "stay"],
    "finance": ["save", "invest", "fund", "money", "bank", "trade", "wealth", "asset", "earn", "pay"],
    "fashion": ["style", "wear", "trend", "chic", "mode", "cloth", "look", "outfit", "brand", "dress"],
    "gaming": ["play", "game", "quest", "level", "clan", "loot", "score", "arena", "pixel", "guild"],
    "beauty": ["glow", "skin", "care", "pure", "soft", "bloom", "radiant", "glam", "silk", "shine"],
}

# Abstract/evocative terms for brandable Stream A, by category
_BRANDABLE_SEEDS: dict[str, list[str]] = {
    "fitness": ["pulse", "surge", "blaze", "lift", "swift", "drive", "core", "peak", "grit", "flex", "forge", "sprint"],
    "crypto": ["forge", "vault", "link", "node", "flux", "spark", "stack", "mesh", "arc", "nexus", "orbit", "prime"],
    "pets": ["paw", "wag", "snug", "romp", "fuzzy", "tails", "cozy", "nuzzle", "frolic", "bounce", "zoomie", "pounce"],
    "tech": ["spark", "flux", "nova", "edge", "orbit", "sync", "forge", "pulse", "apex", "nexus", "grid", "laser"],
    "food": ["bloom", "zest", "crisp", "dash", "blend", "savor", "crunch", "feast", "munch", "drizzle", "simmer", "sizzle"],
    "travel": ["drift", "roam", "soar", "glide", "scout", "forge", "quest", "atlas", "vibe", "wander", "venture", "compass"],
    "finance": ["vault", "forge", "prime", "apex", "yield", "surge", "slate", "guard", "merit", "ledge", "nexus", "ascent"],
    "fashion": ["hue", "chic", "lush", "gleam", "vibe", "sheen", "flair", "bloom", "aura", "crisp", "sleek", "dazzle"],
    "gaming": ["apex", "nexus", "forge", "orbit", "surge", "pulse", "vault", "spark", "blitz", "frag", "clutch", "grind"],
    "beauty": ["glow", "bloom", "aura", "sheen", "gleam", "lush", "radiant", "silk", "pure", "bliss", "velvet", "luminance"],
}

_GENERIC_MEANINGFUL = ["pro", "hub", "lab", "io", "ai", "go", "app", "edge", "peak", "prime"]
_GENERIC_BRANDABLE = ["pulse", "spark", "nova", "forge", "apex", "nexus", "flux", "orbit", "surge", "arc", "edge", "drift", "glow", "bloom", "slate"]


def _category_for_niche(niche: str) -> str:
    niche_lower = niche.lower()
    for cat in _NICHE_SEEDS:
        if cat in niche_lower or niche_lower in cat:
            return cat
    return ""


def _fallback_meaningful(niche: str) -> list[str]:
    cat = _category_for_niche(niche)
    seeds = _NICHE_SEEDS.get(cat, [])
    if not seeds:
        words = [w for w in niche.lower().split() if w.isalpha()]
        seeds = words + _GENERIC_MEANINGFUL
    return list(dict.fromkeys(seeds))[:15]


def _fallback_brandable(niche: str) -> list[str]:
    cat = _category_for_niche(niche)
    seeds = _BRANDABLE_SEEDS.get(cat, [])
    if not seeds:
        seeds = _GENERIC_BRANDABLE
    return list(dict.fromkeys(seeds))[:15]


def fetch_trend_keywords(niche: str, limit: int = 15) -> list[str]:
    """Return trending keywords for the niche. Falls back to curated seeds on error."""
    return fetch_trend_data(niche, limit)["keywords"]


def fetch_trend_data(niche: str, limit: int = 15) -> dict:
    """Return single-stream trend data (backwards-compatible).

    Keys: keywords, pytrends_scores, source
    """
    dual = fetch_dual_trend_streams(niche, limit)
    # Merge both streams for backwards-compatible callers; deduplicate
    all_kws = list(dict.fromkeys(dual["meaningful_keywords"] + dual["brandable_keywords"]))
    return {
        "keywords": all_kws[:limit],
        "pytrends_scores": dual["pytrends_scores"],
        "source": dual["source"],
        "brandable_keywords": dual["brandable_keywords"],
        "meaningful_keywords": dual["meaningful_keywords"],
    }


def fetch_dual_trend_streams(niche: str, limit: int = 15) -> dict:
    """Return two independent trend streams for the niche.

    Returns:
      {
        "brandable_keywords": [...],   # Stream A: abstract/evocative terms
        "meaningful_keywords": [...],  # Stream B: literal niche keywords
        "pytrends_scores": {kw: 0-100},
        "source": "pytrends" | "fallback"
      }

    Both streams run independently. pytrends is optional — the independent
    fallback seeds produce valid output when pytrends is rate-limited.
    """
    try:
        pytrends = TrendReq(hl="en-US", tz=360, timeout=(10, 25), retries=1, backoff_factor=0.5)
        pytrends.build_payload([niche], cat=0, timeframe="today 3-m", geo="", gprop="")
        related = pytrends.related_queries()

        raw_keywords: list[str] = []
        scores: dict[str, int] = {}
        for entry in related.values():
            for df_key, base_score in (("top", 70), ("rising", 85)):
                df = entry.get(df_key)
                if df is not None and not df.empty:
                    has_value = "value" in df.columns
                    for _, row in df.iterrows():
                        kw = str(row["query"])
                        raw_value = row["value"] if has_value else None
                        for token in kw.lower().split():
                            if token.isalpha() and 3 <= len(token) <= 12:
                                raw_keywords.append(token)
                                if raw_value is not None:
                                    scores[token] = max(scores.get(token, 0), min(100, int(raw_value) if raw_value > 0 else base_score))
                                else:
                                    scores[token] = max(scores.get(token, 0), base_score)

        raw_keywords = list(dict.fromkeys(raw_keywords))

        if raw_keywords:
            logger.info("pytrends returned %d keywords for '%s'", len(raw_keywords), niche)
            # Stream B (meaningful) = literal pytrends keywords
            meaningful = raw_keywords[:limit]
            # Stream A (brandable) = category evocatives + any short pytrends tokens
            short_tokens = [k for k in raw_keywords if len(k) <= 6]
            brandable = (short_tokens + _fallback_brandable(niche))[:limit]
            brandable = list(dict.fromkeys(brandable))[:limit]
            return {
                "brandable_keywords": brandable,
                "meaningful_keywords": meaningful,
                "pytrends_scores": scores,
                "source": "pytrends",
            }
    except Exception as exc:
        logger.warning("pytrends failed for '%s': %s – using independent fallback", niche, exc)

    return {
        "brandable_keywords": _fallback_brandable(niche),
        "meaningful_keywords": _fallback_meaningful(niche),
        "pytrends_scores": {},
        "source": "fallback",
    }

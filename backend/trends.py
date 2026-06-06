"""Step 1 - Trend keyword fetch via pytrends with graceful fallback."""

import logging
from pytrends.request import TrendReq

logger = logging.getLogger(__name__)

# Niche-specific seed keywords for fallback when pytrends is rate-limited
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

_GENERIC_SEEDS = ["pro", "hub", "lab", "io", "ai", "go", "app", "edge", "peak", "prime"]


def _fallback_keywords(niche: str) -> list[str]:
    niche_lower = niche.lower()
    seeds = _NICHE_SEEDS.get(niche_lower, [])
    if not seeds:
        # Build generic seeds from the niche word itself
        words = niche_lower.split()
        seeds = words + [w[:4] for w in words if len(w) > 4] + _GENERIC_SEEDS
    return list(dict.fromkeys(seeds))[:15]


def fetch_trend_keywords(niche: str, limit: int = 15) -> list[str]:
    """Return trending keywords for the niche. Falls back to curated seeds on error."""
    try:
        pytrends = TrendReq(hl="en-US", tz=360, timeout=(10, 25), retries=1, backoff_factor=0.5)
        pytrends.build_payload([niche], cat=0, timeframe="today 3-m", geo="", gprop="")
        related = pytrends.related_queries()

        keywords: list[str] = []
        for entry in related.values():
            for df_key in ("top", "rising"):
                df = entry.get(df_key)
                if df is not None and not df.empty:
                    for kw in df["query"].tolist():
                        # extract simple single tokens
                        for token in str(kw).lower().split():
                            if token.isalpha() and 3 <= len(token) <= 12:
                                keywords.append(token)

        keywords = list(dict.fromkeys(keywords))[:limit]
        if keywords:
            logger.info("pytrends returned %d keywords for '%s'", len(keywords), niche)
            return keywords
    except Exception as exc:
        logger.warning("pytrends failed for '%s': %s – using fallback", niche, exc)

    return _fallback_keywords(niche)

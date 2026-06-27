"""Step 4 - Rule-based domain scoring (0-100) plus trend/heat/semantics enrichment."""

import re

import trend_engine
from semantics import classify_and_explain

_VOWELS = set("aeiou")
_AWKWARD_COMBOS = re.compile(r'(xx|zz|qq|vv|ww|ck$|ng$|[bcdfghjklmnpqrstvwxyz]{4,})')
_AMBIGUOUS_ENDINGS = re.compile(r'(rn|ci|cl|li|lj|ji|lo|o0|l1)$')

_EXTENSION_BONUS = {".com": 10, ".net": 5, ".org": 4, ".ai": 8, ".io": 7, ".co": 6, ".app": 5, ".dev": 5, ".store": 3, ".site": 2, ".online": 2}
_REGISTRATION_COST_USD = {".com": 12, ".net": 12, ".org": 16, ".ai": 70, ".store": 5, ".site": 3, ".online": 3, ".co": 30, ".io": 60, ".app": 14, ".dev": 12}


def _length_score(name: str) -> int:
    n = len(name)
    if n <= 6:
        return 100
    if n <= 9:
        return 75
    if n <= 12:
        return 50
    return 25


def _pronounceability_score(name: str) -> int:
    """Score based on consonant-vowel alternation quality."""
    vowel_count = sum(1 for c in name if c in _VOWELS)
    if len(name) == 0:
        return 0

    vowel_ratio = vowel_count / len(name)
    # ideal ratio ~0.35-0.55
    if 0.30 <= vowel_ratio <= 0.55:
        ratio_score = 100
    elif 0.20 <= vowel_ratio < 0.30 or 0.55 < vowel_ratio <= 0.65:
        ratio_score = 70
    else:
        ratio_score = 40

    # penalise runs of 3+ consonants
    consonant_run = max((len(m.group()) for m in re.finditer(r'[bcdfghjklmnpqrstvwxyz]+', name)), default=0)
    run_penalty = min(consonant_run * 10, 40) if consonant_run > 2 else 0

    return max(0, ratio_score - run_penalty)


def _keyword_score(name: str, keywords: list[str]) -> int:
    for kw in keywords:
        if kw in name or name in kw:
            return 100
    for kw in keywords:
        if len(kw) >= 4 and (kw[:4] in name or name[:4] == kw[:4]):
            return 60
    return 0


def _awkward_combo_penalty(name: str) -> int:
    if _AWKWARD_COMBOS.search(name):
        return 20
    if _AMBIGUOUS_ENDINGS.search(name):
        return 10
    return 0


def registration_cost_usd(extension: str) -> int:
    return _REGISTRATION_COST_USD.get(extension, 12)


def score_domain_breakdown(name: str, extension: str, keywords: list[str]) -> dict:
    ls = _length_score(name)
    ps = _pronounceability_score(name)
    ks = _keyword_score(name, keywords)
    penalty = _awkward_combo_penalty(name)
    ext_bonus = _EXTENSION_BONUS.get(extension, 0)
    spelling = max(0, 100 - penalty * 5)

    total = max(0, min(100, round((ls * 0.30) + (ps * 0.30) + (ks * 0.30) + ext_bonus - penalty)))
    return {
        "total": total,
        "breakdown": {
            "length": ls,
            "pronounceability": ps,
            "keyword_match": ks,
            "spelling": spelling,
            "extension": ext_bonus * 10,
        },
    }


def score_domain(name: str, extension: str, keywords: list[str]) -> int:
    return score_domain_breakdown(name, extension, keywords)["total"]


def score_4dimensions(
    name: str,
    extension: str,
    keywords: list[str],
    brandable_keywords: list[str],
    meaningful_keywords: list[str],
    provenance: dict,
    category: str,
    trend_score: int,
) -> dict:
    """Compute the 4 semantic dimension scores (each 0–10) plus total (0–40).

    Dimensions:
      semantic_value    — how meaningful/clear the name is
      trend_relevance   — alignment with current trend keywords
      market_potential  — commercial/resale value signals
      brandability      — how well it works as a brand
    """
    semantic = classify_and_explain(name, provenance)
    name_type = semantic["type"]  # "Brandable" or "Meaningful"

    # 1. Semantic value
    if provenance.get("lexicon_word"):
        sv = 9
    elif provenance.get("english_root") and provenance.get("extra_part"):
        sv = 7
    elif name_type == "Meaningful":
        if any(kw in name for kw in meaningful_keywords):
            sv = 8
        else:
            sv = 6
    else:
        if provenance.get("prefix") or provenance.get("suffix"):
            sv = 5
        elif provenance.get("blend_a"):
            sv = 4
        else:
            sv = 3

    # 2. Trend relevance — how many trend keywords overlap
    all_keywords = list(dict.fromkeys(meaningful_keywords + brandable_keywords + keywords))
    kw_hits = sum(1 for kw in all_keywords if kw in name or name.startswith(kw[:4]))
    if kw_hits >= 2:
        tr = 9
    elif kw_hits == 1:
        tr = 7
    elif any(kw[:3] in name for kw in all_keywords if len(kw) >= 3):
        tr = 5
    else:
        # Use trend_score as a proxy
        tr = max(1, min(6, trend_score // 15))

    # 3. Market potential
    n = len(name)
    ext_val = {".com": 4, ".ai": 3, ".io": 3, ".co": 2, ".net": 2, ".org": 2, ".app": 2, ".dev": 2}.get(extension, 1)
    if n <= 5:
        len_val = 4
    elif n <= 8:
        len_val = 3
    elif n <= 12:
        len_val = 2
    else:
        len_val = 1
    # Category premium bonus
    premium_cats = {"crypto", "tech", "finance", "ai"}
    cat_bonus = 1 if any(p in category for p in premium_cats) else 0
    kw_hit = 1 if any(kw in name for kw in meaningful_keywords) else 0
    mp = min(10, ext_val + len_val + cat_bonus + kw_hit + 1)

    # 4. Brandability
    ps = _pronounceability_score(name)
    if ps >= 90:
        brand_ps = 3
    elif ps >= 70:
        brand_ps = 2
    else:
        brand_ps = 1
    if n <= 6:
        brand_len = 3
    elif n <= 9:
        brand_len = 2
    else:
        brand_len = 1
    # Uniqueness: invented/portmanteau names are more distinctive
    if name_type == "Brandable" and provenance.get("blend_a"):
        brand_unique = 2
    elif name_type == "Brandable":
        brand_unique = 1
    else:
        brand_unique = 0
    ba = min(10, brand_ps + brand_len + brand_unique + 2)

    total_4d = sv + tr + mp + ba

    return {
        "semantic_value": sv,
        "trend_relevance": tr,
        "market_potential": mp,
        "brandability": ba,
        "domain_score_total": total_4d,
    }


def enrich_domain(
    name: str,
    extension: str,
    keywords: list[str],
    provenance: dict,
    category: str,
    trend_location: str,
    pytrends_scores: dict[str, int],
    registrar_availability: dict[str, bool | None],
    available: bool | None = True,
    brandable_keywords: list[str] | None = None,
    meaningful_keywords: list[str] | None = None,
) -> dict:
    """Build the full enriched result for one (name, extension) result row."""
    score_result = score_domain_breakdown(name, extension, keywords)
    total = score_result["total"]

    trend_score = trend_engine.domain_trend_score(name, keywords, category, pytrends_scores)

    checked_exts = list(registrar_availability.keys())
    available_count = sum(1 for v in registrar_availability.values() if v)
    heat = trend_engine.heat_index(trend_score, available_count, len(checked_exts))

    clicks = trend_engine.expected_monthly_clicks(heat, trend_score, total, category)
    geo = trend_engine.geo_breakdown(category, trend_location)

    semantic = classify_and_explain(name, provenance)

    dim_scores = score_4dimensions(
        name=name,
        extension=extension,
        keywords=keywords,
        brandable_keywords=brandable_keywords or [],
        meaningful_keywords=meaningful_keywords or [],
        provenance=provenance,
        category=category,
        trend_score=trend_score,
    )

    return {
        "name": name,
        "extension": extension,
        "available": available,
        "length": len(name),
        "registration_cost_usd": registration_cost_usd(extension),
        "score": total,
        "score_breakdown": score_result["breakdown"],
        "trend_score": trend_score,
        "heat_index": heat,
        "type": semantic["type"],
        "language_origin": semantic["language_origin"],
        "meaning": semantic["meaning"],
        "registrar_availability": registrar_availability,
        "geo_breakdown": geo,
        "expected_monthly_clicks": clicks,
        **dim_scores,
    }

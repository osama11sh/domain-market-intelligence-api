"""Step 4 - Rule-based domain scoring (0-100)."""

import re

_VOWELS = set("aeiou")
_AWKWARD_COMBOS = re.compile(r'(xx|zz|qq|vv|ww|ck$|ng$|[bcdfghjklmnpqrstvwxyz]{4,})')
_AMBIGUOUS_ENDINGS = re.compile(r'(rn|ci|cl|li|lj|ji|lo|o0|l1)$')

_EXTENSION_BONUS = {".com": 10, ".net": 5}
_COM_COST_USD = 12
_NET_COST_USD = 12


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
    consonant_count = len(name) - vowel_count
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
    # partial substring match
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


def registration_cost_usd(extension: str) -> int:
    return _COM_COST_USD if extension == ".com" else _NET_COST_USD

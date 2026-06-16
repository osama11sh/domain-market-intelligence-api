"""Step 2 - Domain name candidate generation.

Each candidate carries a small `provenance` dict describing how it was built
(prefix/suffix used, lexicon word matched, blend pair, etc.) so the semantics
module can classify it as Brandable/Meaningful and write a meaning/construction
explanation without guessing after the fact.
"""

import itertools
import re

from semantics import LEXICON

_PREFIXES = ["get", "go", "my", "the", "try", "use", "be", "we", "hey", "pro", "top", "now"]
_SUFFIXES = ["ly", "io", "co", "hub", "lab", "hq", "ai", "app", "ify", "ster", "er", "ful", "ish", "plus", "zone"]
_PORTMANTEAU_GLUE = ["", "a", "o", "i", "e"]

_VALID_RE = re.compile(r'^[a-z]{3,15}$')


def _valid(name: str) -> bool:
    return bool(_VALID_RE.match(name))


def _portmanteau(a: str, b: str) -> list[str]:
    """Blend end of `a` with start of `b`."""
    results = []
    for cut_a in range(max(1, len(a) - 3), len(a)):
        for cut_b in range(1, min(4, len(b))):
            for glue in _PORTMANTEAU_GLUE:
                merged = a[:cut_a] + glue + b[cut_b:]
                if _valid(merged):
                    results.append(merged)
    return results


def _add(candidates: dict, name: str, provenance: dict) -> None:
    if _valid(name) and name not in candidates:
        candidates[name] = provenance


def _lexicon_candidates(niche_token: str, languages: list[str] | None) -> dict[str, dict]:
    """Build meaningful candidates from the curated multi-language lexicon."""
    out: dict[str, dict] = {}
    allowed = set(languages) if languages else None
    for lang, words in LEXICON.items():
        if allowed is not None and lang not in allowed:
            continue
        for word, meaning in words.items():
            _add(out, word, {"lexicon_word": word, "lexicon_lang": lang, "lexicon_meaning": meaning})
            for suffix in _SUFFIXES[:6]:
                cand = word + suffix
                _add(out, cand, {"lexicon_word": word, "lexicon_lang": lang, "lexicon_meaning": meaning, "extra_part": suffix})
            cand = word + niche_token
            _add(out, cand, {"lexicon_word": word, "lexicon_lang": lang, "lexicon_meaning": meaning, "extra_part": niche_token})
            cand = niche_token + word
            _add(out, cand, {"lexicon_word": word, "lexicon_lang": lang, "lexicon_meaning": meaning, "extra_part": niche_token})
    return out


def generate_candidates(niche: str, keywords: list[str], languages: list[str] | None = None) -> dict[str, dict]:
    """Generate domain name candidates from niche + trend keywords + lexicon.

    Returns a dict of name -> provenance (so callers can both list names and
    explain how each was constructed for semantics/classification).
    """
    niche_token = niche.lower().split()[0][:12]
    all_tokens = list(dict.fromkeys([niche_token] + [k.lower() for k in keywords if k.isalpha()]))

    candidates: dict[str, dict] = {}

    for token in all_tokens:
        _add(candidates, token, {"niche_token": token})

        for prefix in _PREFIXES:
            cand = prefix + token
            _add(candidates, cand, {"prefix": prefix, "root": token})

        for suffix in _SUFFIXES:
            cand = token + suffix
            _add(candidates, cand, {"root": token, "suffix": suffix})

        for prefix in _PREFIXES[:6]:
            for suffix in _SUFFIXES[:6]:
                cand = prefix + token + suffix
                _add(candidates, cand, {"prefix": prefix, "root": token, "suffix": suffix})

    pairs = list(itertools.combinations(all_tokens[:8], 2))
    for a, b in pairs:
        for name in _portmanteau(a, b):
            _add(candidates, name, {"blend_a": a, "blend_b": b})
        for name in _portmanteau(b, a):
            _add(candidates, name, {"blend_a": b, "blend_b": a})

    for a, b in itertools.combinations(all_tokens[:10], 2):
        cand = a + b
        _add(candidates, cand, {"blend_a": a, "blend_b": b})
        cand = b + a
        _add(candidates, cand, {"blend_a": b, "blend_b": a})

    # English-only niches still get multi-language "meaningful" options unless
    # the caller restricted to a specific non-English-only language set.
    lexicon_langs = None if languages is None else [l for l in languages if l != "English"]
    if languages is None or lexicon_langs:
        candidates.update(_lexicon_candidates(niche_token, lexicon_langs))

    # Cap to a sane batch; keep deterministic ordering for reproducible results.
    limited_names = sorted(candidates.keys())[:250]
    return {name: candidates[name] for name in limited_names}

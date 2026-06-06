"""Step 2 - Domain name candidate generation."""

import itertools
import re

_PREFIXES = ["get", "go", "my", "the", "try", "use", "be", "we", "hey", "pro", "top", "now"]
_SUFFIXES = ["ly", "io", "co", "hub", "lab", "hq", "ai", "app", "ify", "ster", "er", "ful", "ish", "plus", "zone"]
_PORTMANTEAU_GLUE = ["", "a", "o", "i", "e"]

_VALID_RE = re.compile(r'^[a-z]{4,15}$')


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


def generate_candidates(niche: str, keywords: list[str]) -> list[str]:
    """Generate ~200 domain name candidates from niche + trend keywords."""
    niche_token = niche.lower().split()[0][:12]
    all_tokens = list(dict.fromkeys([niche_token] + [k.lower() for k in keywords if k.isalpha()]))

    candidates: set[str] = set()

    for token in all_tokens:
        if _valid(token):
            candidates.add(token)

        # prefix + token
        for prefix in _PREFIXES:
            cand = prefix + token
            if _valid(cand):
                candidates.add(cand)

        # token + suffix
        for suffix in _SUFFIXES:
            cand = token + suffix
            if _valid(cand):
                candidates.add(cand)

        # prefix + token + suffix (short combos only)
        for prefix in _PREFIXES[:6]:
            for suffix in _SUFFIXES[:6]:
                cand = prefix + token + suffix
                if _valid(cand):
                    candidates.add(cand)

    # portmanteau of pairs
    pairs = list(itertools.combinations(all_tokens[:8], 2))
    for a, b in pairs:
        for name in _portmanteau(a, b):
            candidates.add(name)
        for name in _portmanteau(b, a):
            candidates.add(name)

    # two-token concatenation
    for a, b in itertools.combinations(all_tokens[:10], 2):
        cand = a + b
        if _valid(cand):
            candidates.add(cand)
        cand = b + a
        if _valid(cand):
            candidates.add(cand)

    return sorted(candidates)[:250]

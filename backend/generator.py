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

# Expanded English word roots for broader candidate generation.
# Covers 3-8 char words that make strong domain building-blocks.
_ENGLISH_ROOTS = [
    # 3-char roots
    "ace", "arc", "art", "awe", "bay", "bee", "bit", "bow", "box", "bud",
    "bus", "cue", "day", "dev", "dew", "dip", "dot", "duo", "elf", "era",
    "fit", "fix", "fly", "fun", "gem", "hue", "hub", "ice", "jet", "joy",
    "key", "kin", "kit", "lab", "law", "led", "log", "lux", "map", "max",
    "mix", "net", "nix", "oak", "opt", "orb", "owl", "own", "pad", "pay",
    "pen", "pit", "pod", "pop", "pro", "pub", "raw", "ray", "ref", "rep",
    "rid", "run", "sap", "set", "sky", "spa", "spy", "sub", "sum", "sun",
    "tab", "tap", "tax", "tea", "tip", "top", "toy", "uni", "van", "vim",
    "vow", "wax", "web", "win", "wit", "wow", "zen", "zip", "zoo",
    # 4-char roots
    "aide", "arch", "atom", "axes", "base", "beat", "best", "bite", "bolt",
    "bond", "book", "buzz", "calm", "camp", "card", "care", "cash", "chip",
    "chat", "cite", "clan", "clip", "club", "code", "coin", "cord", "core",
    "crew", "crop", "cure", "data", "deal", "deck", "deep", "desk", "dial",
    "dive", "done", "dose", "dots", "drag", "draw", "drop", "drum", "dual",
    "duke", "dusk", "duty", "ease", "echo", "edge", "epic", "even", "expo",
    "face", "fact", "fair", "fame", "fast", "feed", "feel", "file", "find",
    "fine", "flag", "flat", "flex", "flip", "flow", "foam", "fold", "font",
    "form", "fork", "fuel", "fuse", "gain", "gate", "gear", "gist", "glad",
    "goal", "gold", "good", "grit", "grip", "glow", "grow", "hack", "halo",
    "heat", "hero", "high", "hint", "hire", "hold", "home", "host", "icon",
    "idea", "idle", "info", "iris", "item", "jump", "keen", "kick", "kind",
    "knot", "lack", "lead", "lean", "leap", "lend", "lift", "link", "list",
    "live", "lock", "logo", "loom", "loot", "loop", "lore", "mark", "meld",
    "mesh", "mind", "mint", "mix", "mode", "mole", "move", "mule", "name",
    "near", "node", "norm", "note", "null", "open", "pace", "page", "park",
    "path", "peak", "pick", "pier", "pike", "pile", "ping", "pipe", "plan",
    "play", "plus", "poll", "pool", "port", "pose", "post", "prop", "push",
    "race", "rack", "rank", "rate", "read", "real", "reef", "rent", "ride",
    "ring", "risk", "road", "rock", "role", "roll", "roof", "root", "rope",
    "rove", "rule", "rush", "safe", "sage", "sail", "sale", "salt", "save",
    "scan", "seal", "seek", "seed", "send", "ship", "shop", "shot", "show",
    "sign", "sink", "site", "skip", "slab", "slim", "slot", "snap", "snow",
    "soil", "sole", "sort", "soul", "span", "spec", "spin", "star", "stay",
    "stem", "step", "stop", "suit", "surf", "sync", "talk", "task", "team",
    "term", "test", "text", "tick", "tier", "time", "tint", "told", "toll",
    "tone", "tool", "tour", "town", "trek", "trim", "trip", "true", "tune",
    "turn", "type", "unit", "used", "user", "view", "vine", "void", "volt",
    "vote", "wake", "walk", "wall", "warp", "wave", "weld", "wire", "wise",
    "wish", "word", "work", "writ", "yard", "zone",
    # additional 4-char roots for richer short-domain coverage
    "bold", "glee", "lush", "noir", "perk", "pure",
    # 5-8 char roots
    "alert", "align", "allow", "apply", "arise", "aside", "atlas", "avoid",
    "basis", "begin", "blade", "blaze", "block", "bloom", "boost", "brand",
    "brave", "break", "brief", "bring", "broad", "build", "cache", "check",
    "choir", "clean", "clear", "click", "cloud", "coach", "coast", "count",
    "cover", "craft", "crate", "creed", "cross", "crowd", "curve", "cycle",
    "daily", "datum", "defer", "delta", "depot", "depth", "draft", "dream",
    "drift", "drive", "drone", "eager", "early", "earth", "emote", "enact",
    "enter", "envoy", "equal", "equip", "event", "exist", "extra", "fable",
    "facet", "faith", "field", "fixed", "flair", "flame", "flare", "fleet",
    "focal", "focus", "forge", "found", "frame", "fresh", "front", "fulcrum",
    "gauge", "given", "glide", "globe", "grace", "grade", "grand", "grant",
    "grasp", "great", "green", "greet", "group", "guard", "guide", "guild",
    "haven", "heart", "hinge", "hoist", "honor", "house", "hover", "human",
    "hyper", "image", "inbox", "index", "indie", "input", "inter", "issue",
    "joint", "judge", "knack", "label", "lance", "layer", "learn", "ledge",
    "level", "light", "lingo", "local", "lodge", "logic", "lumen", "lunar",
    "media", "merge", "merit", "metro", "micro", "model", "mount", "multi",
    "nerve", "niche", "night", "north", "nexus", "ocean", "offer", "onbox",
    "onset", "orbit", "order", "other", "outer", "panel", "pixel", "place",
    "pilot", "pivot", "pitch", "plant", "plate", "plaza", "point", "polar",
    "power", "press", "price", "prime", "print", "probe", "proof", "pulse",
    "query", "quick", "quiet", "quota", "quote", "radar", "raise", "rally",
    "realm", "relay", "remix", "renew", "repro", "reset", "reach", "review",
    "ridge", "right", "river", "round", "route", "royal", "ruler", "scale",
    "scene", "scope", "scout", "sharp", "shift", "shore", "sight", "skill",
    "slate", "slide", "slope", "smart", "solar", "solve", "south", "space",
    "spark", "speed", "spend", "split", "squad", "stack", "stake", "start",
    "state", "steel", "stone", "store", "storm", "story", "strap", "strat",
    "study", "style", "super", "surge", "swift", "swiss", "table", "theme",
    "think", "third", "title", "touch", "trace", "track", "trade", "trail",
    "train", "trait", "trend", "tribe", "trick", "trust", "truth", "turbo",
    "ultra", "union", "unity", "until", "upper", "urban", "usage", "vault",
    "vance", "value", "verse", "video", "vigor", "viral", "vista", "vital",
    "voice", "watch", "water", "world", "worth", "write", "yield",
    # additional 5-char roots for stronger brand vocabulary
    "bliss", "brisk", "charm", "crisp", "gleam", "noble", "pride", "quest",
    "shine", "valor", "vivid", "zesty",
]

_VALID_RE = re.compile(r'^[a-z]{1,20}$')


def _valid(name: str) -> bool:
    return bool(_VALID_RE.match(name))


def _portmanteau(a: str, b: str) -> list[str]:
    """Blend beginning of `a` with end of `b`, ensuring both halves are substantial."""
    results = []
    if len(a) < 4 or len(b) < 4:
        return results
    # Take first portion of a (at least half)
    for cut_a in range(max(2, len(a) - 3), len(a) - 1):
        # Take last portion of b — start from at least halfway through b
        for cut_b in range(max(len(b) // 2, 3), len(b) - 1):
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


def _english_root_candidates(niche_token: str, top_tokens: list[str]) -> dict[str, dict]:
    """Build candidates from the curated English roots wordbank."""
    out: dict[str, dict] = {}
    for root in _ENGLISH_ROOTS:
        _add(out, root, {"english_root": root})
        for token in top_tokens[:3]:
            cand = root + token
            _add(out, cand, {"english_root": root, "extra_part": token})
            cand = token + root
            _add(out, cand, {"extra_part": token, "english_root": root})
        for prefix in _PREFIXES[:6]:
            cand = prefix + root
            _add(out, cand, {"prefix": prefix, "root": root})
        for suffix in _SUFFIXES[:6]:
            cand = root + suffix
            _add(out, cand, {"root": root, "suffix": suffix})
    return out


def generate_candidates(niche: str, keywords: list[str], languages: list[str] | None = None) -> dict[str, dict]:
    """Generate domain name candidates from niche + trend keywords + lexicon + English roots.

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

    # Expand with broad English roots wordbank for richer short-domain candidates.
    candidates.update(_english_root_candidates(niche_token, all_tokens))

    # Prioritise niche/keyword-containing names, then shorter names, then alpha.
    def _priority(name: str) -> tuple:
        is_niche = 0 if any(tok in name for tok in all_tokens) else 1
        return (is_niche, len(name), name)

    all_sorted = sorted(candidates.keys(), key=_priority)
    limited_names = all_sorted[:350]
    return {name: candidates[name] for name in limited_names}

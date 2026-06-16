"""Domain semantics - type classification, language origin, meaning/construction text.

Pure rule-based, no external dependency. Covers a small curated multi-language
lexicon so non-English-looking brandable names get an origin + meaning, and a
connotation map for the brandable prefix/suffix engine so every domain (even
invented coinages) gets a human-readable construction explanation.
"""

# word -> English gloss, per language. Romanized where applicable (Japanese).
LEXICON: dict[str, dict[str, str]] = {
    "Spanish": {
        "sol": "sun", "luna": "moon", "fuego": "fire", "agua": "water", "mar": "sea",
        "cielo": "sky", "vida": "life", "amor": "love", "rapido": "fast", "fuerte": "strong",
        "ola": "wave", "pico": "peak", "sueno": "dream", "luz": "light", "viento": "wind",
    },
    "French": {
        "lune": "moon", "soleil": "sun", "feu": "fire", "eau": "water", "mer": "sea",
        "ciel": "sky", "vie": "life", "amour": "love", "rapide": "fast", "fort": "strong",
        "vague": "wave", "reve": "dream", "lumiere": "light", "vent": "wind",
    },
    "German": {
        "sonne": "sun", "mond": "moon", "feuer": "fire", "wasser": "water", "meer": "sea",
        "himmel": "sky", "leben": "life", "liebe": "love", "schnell": "fast", "stark": "strong",
        "welle": "wave", "traum": "dream", "licht": "light", "wind": "wind",
    },
    "Italian": {
        "sole": "sun", "fuoco": "fire", "acqua": "water", "mare": "sea",
        "cielo": "sky", "vita": "life", "amore": "love", "veloce": "fast", "forte": "strong",
        "onda": "wave", "sogno": "dream", "luce": "light", "vento": "wind",
    },
    "Portuguese": {
        "lua": "moon", "fogo": "fire", "ceu": "sky",
        "onda": "wave", "sonho": "dream",
    },
    "Japanese": {
        "hikari": "light", "sora": "sky", "umi": "sea", "kaze": "wind", "tsuki": "moon",
        "taiyo": "sun", "yume": "dream", "hayai": "fast", "nami": "wave", "mori": "forest",
        "kumo": "cloud", "hoshi": "star",
    },
    "Latin": {
        "nova": "new", "omni": "all", "vero": "true", "magna": "great", "prima": "first",
        "terra": "earth", "via": "way", "veritas": "truth",
    },
}

SUPPORTED_LANGUAGES = ["English"] + list(LEXICON.keys())

_PREFIX_CONNO = {
    "get": "action-oriented", "go": "momentum/action", "my": "personal/ownership",
    "the": "definitive/authority", "try": "trial/approachable", "use": "utility-focused",
    "be": "identity/aspirational", "we": "community", "hey": "casual/friendly",
    "pro": "professional/expert", "top": "premium/leading", "now": "urgency/immediacy",
}
_SUFFIX_CONNO = {
    "ly": "trendy app-style suffix", "io": "tech/startup suffix", "co": "company shorthand",
    "hub": "central gathering place", "lab": "experimental/innovative", "hq": "headquarters/authority",
    "ai": "AI/tech association", "app": "software product", "ify": "transformation (Spotify-style)",
    "ster": "casual agent suffix", "er": "agent/doer suffix", "ful": "abundance",
    "ish": "approximate/playful", "plus": "premium/added value", "zone": "dedicated space",
}


def lookup_lexicon_word(token: str) -> tuple[str, str] | None:
    """Return (language, meaning) if token is a known foreign-language root word."""
    for lang, words in LEXICON.items():
        if token in words:
            return lang, words[token]
    return None


def classify_and_explain(name: str, provenance: dict) -> dict:
    """Classify a candidate as Brandable/Meaningful and build a meaning/construction string.

    `provenance` carries hints left by the generator: lexicon_word, lexicon_lang,
    lexicon_meaning, prefix, suffix, blend_a, blend_b, niche_token.
    """
    if provenance.get("lexicon_word"):
        lang = provenance["lexicon_lang"]
        meaning = provenance["lexicon_meaning"]
        word = provenance["lexicon_word"]
        extra = provenance.get("extra_part")
        if extra:
            return {
                "type": "Meaningful",
                "language_origin": lang,
                "meaning": f"Contains '{word}' ({lang} for '{meaning}') combined with '{extra}'",
            }
        return {
            "type": "Meaningful",
            "language_origin": lang,
            "meaning": f"'{word}' means '{meaning}' in {lang}",
        }

    prefix = provenance.get("prefix")
    suffix = provenance.get("suffix")
    if prefix or suffix:
        parts = []
        if prefix:
            parts.append(f"'{prefix}' ({_PREFIX_CONNO.get(prefix, 'stylistic prefix')})")
        root = provenance.get("root", "")
        if root:
            parts.append(f"'{root}'")
        if suffix:
            parts.append(f"'{suffix}' ({_SUFFIX_CONNO.get(suffix, 'stylistic suffix')})")
        return {
            "type": "Brandable",
            "language_origin": "Invented",
            "meaning": "Brandable: " + " + ".join(parts),
        }

    blend_a, blend_b = provenance.get("blend_a"), provenance.get("blend_b")
    if blend_a and blend_b:
        return {
            "type": "Brandable",
            "language_origin": "Invented",
            "meaning": f"Brandable blend of '{blend_a}' and '{blend_b}' — invented coinage",
        }

    niche_token = provenance.get("niche_token")
    if niche_token:
        return {
            "type": "Meaningful",
            "language_origin": "English",
            "meaning": f"Directly references the niche term '{niche_token}'",
        }

    return {
        "type": "Brandable",
        "language_origin": "Invented",
        "meaning": "Brandable coinage with no fixed dictionary meaning",
    }

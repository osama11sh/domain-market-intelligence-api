"""Domain semantics - type classification, language origin, meaning/construction text.

Pure rule-based, no external dependency. Covers a curated multi-language lexicon
so non-English-looking brandable names get an origin + meaning, and a connotation
map for the brandable prefix/suffix engine so every domain (even invented coinages)
gets a human-readable construction explanation.

Non-Latin-script languages (Arabic, Chinese, Japanese, Hindi) use romanized
forms so candidates satisfy ICANN registration constraints (a-z only). The
transliteration system used is recorded in _LANGUAGE_META and surfaced in the
meaning field for transparency.
"""

# word -> English gloss, per language. Non-Latin scripts use romanized forms.
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
        "sole": "sun", "luna": "moon", "fuoco": "fire", "acqua": "water", "mare": "sea",
        "cielo": "sky", "vita": "life", "amore": "love", "veloce": "fast", "forte": "strong",
        "onda": "wave", "sogno": "dream", "luce": "light", "vento": "wind",
        "nuovo": "new", "bello": "beautiful", "grande": "great", "verde": "green",
        "oro": "gold", "rosa": "rose/pink", "caro": "dear/precious",
    },
    "Greek": {
        # Ancient/Modern Greek romanized — all a-z, ICANN-compliant
        "kairos": "the right moment/opportunity", "logos": "word/reason/logic",
        "astra": "stars", "neos": "new", "zoe": "life", "gaia": "earth",
        "phos": "light", "kyma": "wave", "cosmos": "universe/order",
        "arete": "excellence/virtue", "nous": "mind/intellect",
        "arche": "origin/beginning", "telos": "purpose/ultimate aim",
        "agon": "contest/struggle toward excellence", "axios": "worthy",
        "dynamis": "power/potential", "eidos": "form/idea", "ergon": "work/function",
        "ethos": "character/spirit", "mythos": "story/narrative",
        "onoma": "name", "pathos": "emotion/experience", "soma": "body",
        "techne": "craft/skill", "topos": "place", "chronos": "time",
    },
    "Portuguese": {
        "lua": "moon", "fogo": "fire", "ceu": "sky",
        "onda": "wave", "sonho": "dream",
    },
    "Japanese": {
        # Hepburn romanization — all a-z, ICANN-compliant
        "hikari": "light", "sora": "sky", "umi": "sea", "kaze": "wind", "tsuki": "moon",
        "taiyo": "sun", "yume": "dream", "hayai": "fast", "nami": "wave", "mori": "forest",
        "kumo": "cloud", "hoshi": "star",
    },
    "Latin": {
        "nova": "new", "omni": "all", "vero": "true", "magna": "great", "prima": "first",
        "terra": "earth", "via": "way", "veritas": "truth",
    },
    "Arabic": {
        # ALA-LC romanization (simplified) — all a-z, ICANN-compliant
        "noor": "light", "sama": "sky", "bahr": "sea", "najm": "star",
        "qamar": "moon", "shams": "sun", "hayat": "life", "amal": "hope",
        "zaman": "time", "salam": "peace", "fikra": "idea", "khair": "good",
        "watan": "homeland", "rawda": "garden", "fajr": "dawn",
        # Expanded Arabic vocabulary for richer domain candidates
        "nasr": "victory", "majd": "glory", "nada": "dew", "sabah": "morning",
        "huda": "guidance", "ward": "rose", "nour": "radiant", "rahma": "mercy",
        "karam": "generosity", "yaqin": "certainty", "faris": "knight",
        "basim": "smiling", "alam": "world", "darb": "path", "masaa": "evening",
        "ilm": "knowledge", "adl": "justice", "aman": "safety", "badr": "full moon",
        "diyaa": "glow", "falah": "success", "hilal": "crescent", "ishraq": "radiance",
        "jawhar": "essence", "kamal": "perfection", "lujain": "silver",
        "marjan": "coral", "nizam": "order", "omran": "prosperity",
    },
    "Chinese": {
        # Pinyin romanization (without tone marks) — all a-z, ICANN-compliant
        "ming": "bright/brilliant", "feng": "wind/phoenix", "yun": "cloud",
        "xin": "heart/new", "hao": "good/excellent", "bao": "treasure",
        "jin": "gold", "lan": "blue/orchid", "mei": "beautiful",
        "zhi": "wisdom", "guang": "light/bright", "hui": "wisdom/grace",
        "tian": "sky/heaven", "xing": "star", "jing": "essence/capital",
        "chun": "spring", "qing": "clear/blue", "yuan": "source/garden",
        "long": "dragon", "hu": "tiger", "lin": "forest", "wan": "ten thousand",
        "dao": "way/path", "he": "harmony", "rui": "auspicious",
    },
    "Hindi": {
        # Hunterian romanization — all a-z, ICANN-compliant
        "shakti": "power/energy", "prana": "life force", "karma": "action/fate",
        "yoga": "union", "seva": "service", "rishi": "sage", "veda": "knowledge",
        "disha": "direction", "gyan": "wisdom", "surya": "sun",
        "chandra": "moon", "vayu": "wind", "agni": "fire", "jal": "water",
        "asha": "hope", "jaya": "victory", "mitra": "friend", "satya": "truth",
        "ananda": "bliss", "nidhi": "treasure", "maya": "wonder/magic",
        "dharma": "duty/order", "mukti": "freedom", "priya": "beloved",
        "urja": "energy", "prayas": "effort", "srijan": "creation",
    },
}

SUPPORTED_LANGUAGES = ["English"] + list(LEXICON.keys())

# Language family and transliteration metadata — used in meaning explanations.
_LANGUAGE_META: dict[str, dict[str, str]] = {
    "Spanish":    {"family": "Indo-European / Romance",      "romanization": ""},
    "French":     {"family": "Indo-European / Romance",      "romanization": ""},
    "German":     {"family": "Indo-European / Germanic",     "romanization": ""},
    "Italian":    {"family": "Indo-European / Romance",      "romanization": ""},
    "Portuguese": {"family": "Indo-European / Romance",      "romanization": ""},
    "Japanese":   {"family": "Japonic",                      "romanization": "Hepburn romanization"},
    "Latin":      {"family": "Indo-European / Italic",       "romanization": ""},
    "Arabic":     {"family": "Afro-Asiatic / Semitic",       "romanization": "ALA-LC romanization"},
    "Chinese":    {"family": "Sino-Tibetan",                 "romanization": "Pinyin romanization"},
    "Hindi":      {"family": "Indo-European / Indo-Aryan",   "romanization": "Hunterian romanization"},
    "Greek":      {"family": "Indo-European / Hellenic",     "romanization": "Greek romanization"},
    "English":    {"family": "Indo-European / Germanic",     "romanization": ""},
}

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

# Cross-cultural and semantic connotation risks — noted inside the meaning string.
_CONNOTATION_RISKS: dict[str, str] = {
    "gift":  "means 'poison' in German, Swedish, Danish, and Norwegian",
    "mist":  "means 'manure/dung' in German",
    "bald":  "means 'soon' in German; associated with hair loss in English",
    "fart":  "offensive in English",
    "dump":  "carries negative connotation (rubbish, discarding)",
    "doom":  "strongly negative — ruin and fate",
    "drab":  "negative — dull and colourless",
    "grim":  "negative — harsh and joyless",
    "dire":  "negative — extremely serious",
    "ruin":  "negative — destruction",
    "nadir": "negative — lowest point (opposite of zenith)",
    "slag":  "offensive in British English",
}

# Meanings for non-obvious English words that commonly appear as domain names.
_ENGLISH_DOMAIN_GLOSSARY: dict[str, str] = {
    # Latin/classical borrowings common in tech branding
    "nexus": "central connection point",
    "apex": "highest point; peak of achievement",
    "flux": "continuous change and flow",
    "lumen": "unit of luminous output; brightness",
    "delta": "change or difference; fourth Greek letter",
    "sigma": "quality and precision; Greek letter for 'sum'",
    "axiom": "self-evident truth or principle",
    "crux": "the decisive or most important point",
    "rune": "ancient symbol; mysterious character",
    "aura": "distinctive atmosphere surrounding a person or place",
    "nova": "bright new star; something new and brilliant",
    "orb": "spherical object; globe of light",
    # Brand-positive English words
    "grit": "perseverance and determination",
    "lore": "accumulated knowledge and tradition",
    "meld": "blend together harmoniously",
    "sage": "deeply wise; the herb associated with clarity",
    "halo": "aura of positive association",
    "boon": "welcome benefit or advantage",
    "flair": "natural talent and stylish quality",
    "vim": "energy and enthusiasm",
    "zeal": "great energy and enthusiasm",
    "acme": "peak of achievement",
    "brio": "vigour and vivacity",
    "elan": "energetic style and enthusiasm",
    "verve": "enthusiasm and vitality",
    "valor": "great courage in the face of danger",
    "gleam": "bright flash of light; to shine brightly",
    "bliss": "perfect happiness and joy",
    "brisk": "active, energetic, and efficient",
    "crisp": "clean, sharp, and refreshing",
    "vivid": "producing powerful feelings; intensely bright",
    "noble": "having high moral qualities",
    "quest": "a long and difficult search for something",
    "charm": "power to delight and attract",
    "pride": "deep satisfaction from one's own achievements",
    "shine": "emit bright light; excel",
    # Tech-specific
    "cache": "fast-access data store",
    "node": "connection point in a network",
    "pixel": "smallest unit of a digital image",
    "parse": "analyse and interpret structured data",
    "pivot": "central point of rotation; strategic change in direction",
}


def lookup_lexicon_word(token: str) -> tuple[str, str] | None:
    """Return (language, meaning) if token is a known foreign-language root word."""
    for lang, words in LEXICON.items():
        if token in words:
            return lang, words[token]
    return None


def _romanization_note(lang: str) -> str:
    """Return a parenthetical romanization note for non-Latin-script languages."""
    rom = _LANGUAGE_META.get(lang, {}).get("romanization", "")
    return f", {rom}" if rom else ""


def _connotation_note(name: str) -> str:
    """Return a risk note if any substring of `name` is in the connotation risk table."""
    for word, risk in _CONNOTATION_RISKS.items():
        if word in name:
            return f" ⚠ Cross-cultural note: '{word}' {risk}."
    return ""


def _phonetic_descriptor(name: str) -> str:
    """Short phonetic quality label for pure invented coinages."""
    vowels = "aeiou"
    vowel_count = sum(1 for c in name if c in vowels)
    ratio = vowel_count / len(name) if name else 0
    traits = []
    if len(name) <= 5:
        traits.append("short and punchy")
    if 0.33 <= ratio <= 0.55:
        traits.append("phonetically balanced")
    if name and name[-1] in vowels:
        traits.append("open vowel ending (easy to say)")
    return ", ".join(traits) if traits else "invented coinage"


def classify_and_explain(name: str, provenance: dict) -> dict:
    """Classify a candidate as Brandable/Meaningful and build a meaning/construction string.

    `provenance` carries hints left by the generator: lexicon_word, lexicon_lang,
    lexicon_meaning, prefix, suffix, blend_a, blend_b, niche_token, english_root.
    A connotation risk note is appended inline when the name contains a known risk word.
    """
    risk = _connotation_note(name)

    if provenance.get("lexicon_word"):
        lang = provenance["lexicon_lang"]
        meaning = provenance["lexicon_meaning"]
        word = provenance["lexicon_word"]
        extra = provenance.get("extra_part")
        rom = _romanization_note(lang)
        if extra:
            return {
                "type": "Meaningful",
                "language_origin": lang,
                "meaning": f"Contains '{word}' ({lang}{rom} for '{meaning}') combined with '{extra}'" + risk,
            }
        return {
            "type": "Meaningful",
            "language_origin": lang,
            "meaning": f"'{word}' means '{meaning}' in {lang}{rom}" + risk,
        }

    english_root = provenance.get("english_root")
    if english_root:
        extra = provenance.get("extra_part", "")
        gloss = _ENGLISH_DOMAIN_GLOSSARY.get(english_root, "")
        root_desc = f"'{english_root}'" + (f" ({gloss})" if gloss else "")
        if extra:
            suffix_hint = _SUFFIX_CONNO.get(extra, "")
            extra_desc = f"'{extra}'" + (f" — {suffix_hint}" if suffix_hint else "")
            return {
                "type": "Meaningful",
                "language_origin": "English",
                "meaning": f"Combines {root_desc} with {extra_desc}" + risk,
            }
        return {
            "type": "Meaningful",
            "language_origin": "English",
            "meaning": f"Based on the English word {root_desc}" + risk,
        }

    prefix = provenance.get("prefix")
    suffix = provenance.get("suffix")
    if prefix or suffix:
        parts = []
        if prefix:
            parts.append(f"'{prefix}' ({_PREFIX_CONNO.get(prefix, 'stylistic prefix')})")
        root = provenance.get("root", "")
        if root:
            gloss = _ENGLISH_DOMAIN_GLOSSARY.get(root, "")
            parts.append(f"'{root}'" + (f" ({gloss})" if gloss else ""))
        if suffix:
            parts.append(f"'{suffix}' ({_SUFFIX_CONNO.get(suffix, 'stylistic suffix')})")
        return {
            "type": "Brandable",
            "language_origin": "Invented",
            "meaning": "Brandable: " + " + ".join(parts) + risk,
        }

    blend_a, blend_b = provenance.get("blend_a"), provenance.get("blend_b")
    if blend_a and blend_b:
        return {
            "type": "Brandable",
            "language_origin": "Invented",
            "meaning": f"Brandable blend of '{blend_a}' and '{blend_b}' — invented coinage" + risk,
        }

    niche_token = provenance.get("niche_token")
    if niche_token:
        gloss = _ENGLISH_DOMAIN_GLOSSARY.get(niche_token, "")
        desc = f"'{niche_token}'" + (f" ({gloss})" if gloss else "")
        return {
            "type": "Meaningful",
            "language_origin": "English",
            "meaning": f"Directly uses the niche keyword {desc}" + risk,
        }

    phonetic = _phonetic_descriptor(name)
    return {
        "type": "Brandable",
        "language_origin": "Invented",
        "meaning": f"Invented brandable name — {phonetic}" + risk,
    }

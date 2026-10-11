"""Mixed-script and confusable (homoglyph) token detection.

Data: a pinned subset of the Unicode ``confusables.txt`` (UTS #39, version 15.1.0)
covering Cyrillic, Greek, Armenian and Latin-extended letters that are commonly
mistaken for ASCII letters, plus NFKC for fullwidth/mathematical forms. The
skeleton computed here is an *approximate* UTS #39 skeleton used for comparison
only; it never replaces the original text.

Non-Latin text is legitimate: whole tokens in another script are only reviewed
when they sit in a predominantly Latin line and their skeleton is a
security-sensitive word.
"""

from __future__ import annotations

import re
import unicodedata

from ..schemas import Severity
from .common import AnnotationSink, cp, cp_label, hidden_match
from .patterns import SENSITIVE_WORDS
from .static_rules import RuleMatch

DETECTOR = "unicode.confusables.v1"
CONFUSABLES_VERSION = "UTS39 confusables.txt 15.1.0 (pinned subset of {n} entries) + NFKC"

CONFUSABLE_MAP: dict[str, str] = {
    # Cyrillic lowercase
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x",
    "ѕ": "s", "і": "i", "ј": "j", "ԁ": "d", "һ": "h", "ӏ": "l", "ԛ": "q",
    "ԝ": "w", "ү": "y", "ѵ": "v",
    # Cyrillic uppercase
    "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H", "О": "O",
    "Р": "P", "С": "C", "Т": "T", "Х": "X", "У": "Y", "Ѕ": "S", "І": "I",
    "Ј": "J", "Ԛ": "Q", "Ԝ": "W", "Ү": "Y", "Ӏ": "l", "З": "3", "Ѵ": "V",
    # Greek
    "α": "a", "ο": "o", "ρ": "p", "ν": "v", "ι": "i", "υ": "u",
    "χ": "x", "γ": "y", "ϲ": "c", "ϳ": "j", "Α": "A", "Β": "B", "Ε": "E",
    "Ζ": "Z", "Η": "H", "Ι": "I", "Κ": "K", "Μ": "M", "Ν": "N", "Ο": "O",
    "Ρ": "P", "Τ": "T", "Υ": "Y", "Χ": "X", "Ϲ": "C", "Ϳ": "J",
    # Armenian
    "օ": "o", "ս": "u", "ց": "g", "հ": "h", "ո": "n", "զ": "q",
    "Տ": "S", "Օ": "O", "Լ": "L",
    # Latin look-alikes
    "ı": "i", "ɑ": "a", "ɡ": "g", "ᴏ": "o", "ɩ": "i",
    "ǃ": "!", "ⅰ": "i", "ⅼ": "l", "ℓ": "l",
}

CONFUSABLES_VERSION = CONFUSABLES_VERSION.format(n=len(CONFUSABLE_MAP))

_TOKEN = re.compile(r"[^\W_][\w.\-@/]*[^\W_]|[^\W_]", re.UNICODE)


def _script(ch: str) -> str:
    if not ch.isalpha():
        return "COMMON"
    name = unicodedata.name(ch, "")
    if name.startswith(("FULLWIDTH LATIN", "MATHEMATICAL")):
        return "COMPAT"
    return name.split(" ", 1)[0] if name else "UNKNOWN"


def skeleton(token: str) -> str:
    out = []
    for ch in token:
        if ch in CONFUSABLE_MAP:
            out.append(CONFUSABLE_MAP[ch])
        else:
            out.append(unicodedata.normalize("NFKC", ch))
    return "".join(out)


def _sensitive(skel: str) -> bool:
    low = skel.lower()
    parts = set(re.split(r"[^a-z0-9]+", low))
    if parts & SENSITIVE_WORDS:
        return True
    return any(w in low for w in ("password", "secret", "token", "apikey", "credential", "admin", "login"))


def _looks_like_identifier(token: str) -> bool:
    return bool(re.search(r"[.@/_-]", token))


def scan(text: str, sink: AnnotationSink) -> list[RuleMatch]:
    matches: list[RuleMatch] = []
    for line_m in re.finditer(r"[^\n]*", text):
        line = line_m.group(0)
        if not line.strip():
            continue
        letters = [c for c in line if c.isalpha()]
        latin_ratio = (sum(1 for c in letters if _script(c) == "LATIN") / len(letters)) if letters else 0
        for tm in _TOKEN.finditer(line):
            token = tm.group(0)
            scripts = {_script(c) for c in token if c.isalpha()}
            scripts.discard("COMMON")
            if not scripts or scripts == {"LATIN"}:
                continue
            mixed = "LATIN" in scripts and len(scripts) > 1
            compat = "COMPAT" in scripts
            confusable_chars = [c for c in token if c in CONFUSABLE_MAP]
            whole_foreign = not mixed and confusable_chars and len(token) >= 3 and latin_ratio >= 0.6 and all(
                (c in CONFUSABLE_MAP) or not c.isalpha() for c in token
            )
            if not (mixed and (confusable_chars or compat)) and not whole_foreign and not (compat and latin_ratio >= 0.6):
                continue
            skel = skeleton(token)
            sensitive = _sensitive(skel) or _looks_like_identifier(skel)
            sev = Severity.medium if sensitive else Severity.low
            if whole_foreign and not sensitive:
                continue  # an ordinary foreign word that happens to look Latin
            start = line_m.start() + tm.start()
            end = line_m.start() + tm.end()
            subs = [c for c in token if c in CONFUSABLE_MAP or _script(c) == "COMPAT"]
            sub_desc = ", ".join(f"{cp_label(c)} → '{skeleton(c)}'" for c in dict.fromkeys(subs))
            aid = sink.add(
                "confusable", start, end, DETECTOR, sev,
                f"Scripts in token: {', '.join(sorted(scripts))}. Substituted: {sub_desc}",
                ", ".join(cp(c) for c in dict.fromkeys(subs)), "; ".join(cp_label(c) for c in dict.fromkeys(subs)),
                skeleton=skel,
            )
            matches.append(hidden_match(
                "SS-UNI-005", "confusable", "Possible confusable / mixed-script token", sev, start, end,
                "The token mixes scripts or uses look-alike characters, so it can appear to be "
                f"{skel!r} while being a different string."
                + (" The look-alike resembles a security-sensitive word or identifier." if sensitive else "")
                + " This is a spoofing indicator, not proof of intent.",
                "Replace the look-alike characters with the intended ASCII letters, or confirm the script is intentional.",
                f"Token {token!r} contains {sub_desc}. Comparison skeleton (not the source): {skel!r}.", [aid],
                skeleton=skel,
            ))
    return matches

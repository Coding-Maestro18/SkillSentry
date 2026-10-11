"""Shared, versioned vocabulary used by the deterministic analyzers."""

from __future__ import annotations

import re

SENSITIVE_WORDS = {
    "password", "passwd", "secret", "secrets", "token", "tokens", "apikey", "api_key", "credential",
    "credentials", "private", "privatekey", "ssh", "id_rsa", "env", "aws", "admin", "root", "sudo",
    "login", "auth", "oauth", "bearer", "wallet", "seed", "mnemonic", "bank", "paypal", "github",
    "google", "microsoft", "openai", "anthropic", "system", "ignore", "override", "bypass", "execute",
    "shell", "bash", "curl", "wget", "upload", "send", "exfiltrate", "webhook", "http", "https",
    "instructions", "developer", "key", "keys", "verify", "account", "cookie", "session",
}

NEGATION = re.compile(
    r"\b(never|not|don['’]?t|do\s+not|must\s+not|should\s+not|shouldn['’]?t|avoid|refuse|refrain|without\s+ever|no\s+one)\b",
    re.IGNORECASE,
)

SECRET_TARGET = (
    r"(?:api[\s_-]?keys?|secret[\s_-]?keys?|access[\s_-]?keys?|private[\s_-]?keys?|ssh[\s_-]?keys?|passwords?|"
    r"credentials?|auth(?:entication)?[\s_-]?tokens?|bearer\s+tokens?|session\s+tokens?|tokens?|secrets?|"
    r"\.env\b|env(?:ironment)?\s+var(?:iable)?s?|id_rsa|aws_secret_access_key|\.aws/credentials|"
    r"\.ssh/|cookies?|seed\s+phrases?|mnemonic)"
)

DISCLOSE_VERB = (
    r"(?:reveal|print|output|echo|display|show|send|share|include|leak|exfiltrate|upload|post|copy|dump|"
    r"read|cat|collect|gather|extract|transmit|forward|paste|attach|email|log|expose|return)"
)

IMPERATIVE_START = re.compile(
    r"^\s*(?:[-*>]\s*)?(?:please\s+)?(?:always|never|you\s+must|you\s+should|you\s+are|ignore|disregard|"
    r"forget|override|bypass|send|upload|post|read|print|reveal|output|execute|run|call|invoke|fetch|"
    r"open|write|delete|copy|include|tell|do\s+not|don['’]t|assistant|ai\s*:|system\s*:|note\s+to\s+(?:the\s+)?"
    r"(?:ai|assistant|model|agent))\b",
    re.IGNORECASE,
)

URL = re.compile(r"\bhttps?://[^\s<>\"'`)\]]+", re.IGNORECASE)
WORD = re.compile(r"[^\W_]+(?:[\u200b-\u200d\u2060\u00ad][^\W_]+)*", re.UNICODE)


def is_negated(sentence_prefix: str) -> bool:
    return bool(NEGATION.search(sentence_prefix))


def sentence_bounds(text: str, start: int, end: int) -> tuple[int, int]:
    """Return the bounds of the sentence/line containing [start, end)."""
    s = max(text.rfind("\n", 0, start), text.rfind(". ", 0, start), text.rfind("! ", 0, start),
            text.rfind("? ", 0, start))
    s = 0 if s < 0 else s + 1
    e_candidates = [i for i in (text.find("\n", end), text.find(". ", end)) if i >= 0]
    e = min(e_candidates) if e_candidates else len(text)
    return s, e

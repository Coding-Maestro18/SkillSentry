"""Deterministic, explainable instruction rules.

Each rule has a stable ID, a contextual trigger and visible rationale. Rules are
triage signals, not proof of intent. Mentions inside a negated sentence ("never
reveal API keys") are skipped so that safety guidance is not flagged.
"""

from __future__ import annotations

import base64
import binascii
import re
from dataclasses import dataclass, field
from typing import Callable, Optional

from ..schemas import Severity
from .patterns import DISCLOSE_VERB, NEGATION, SECRET_TARGET, URL, sentence_bounds


@dataclass
class RuleMatch:
    rule_id: str
    category: str
    title: str
    severity: Severity
    start: int
    end: int
    rationale: str
    remediation: str
    observed: str
    decoded_payload: Optional[str] = None
    decoder: Optional[str] = None
    extra: dict = field(default_factory=dict)


@dataclass
class Rule:
    rule_id: str
    category: str
    title: str
    severity: Severity
    pattern: re.Pattern
    rationale: str
    remediation: str
    skip_if_negated: bool = True
    post: Optional[Callable[[re.Match, str], Optional[dict]]] = None


def _flags(p: str) -> re.Pattern:
    return re.compile(p, re.IGNORECASE)


def _exfil_post(m: re.Match, text: str) -> Optional[dict]:
    url = URL.search(m.group(0))
    return {"destination": url.group(0).rstrip(".,;:") if url else m.group("dest")}


def _shell_post(m: re.Match, text: str) -> Optional[dict]:
    if re.search(r"\|\s*(?:ba|z)?sh\b", m.group(0)):
        return {"severity": Severity.high}
    return {}


RULES: list[Rule] = [
    Rule(
        "SS-OVR-001", "instruction_override", "Instruction to override prior or system rules", Severity.high,
        _flags(
            r"\b(?:ignore|disregard|forget|override|bypass|circumvent)\b[^.\n]{0,40}?"
            r"\b(?:all|any|previous|prior|above|earlier|system|developer|safety|your|the)\b[^.\n]{0,30}?"
            r"\b(?:instructions?|rules?|prompts?|guidelines?|safeguards?|restrictions?|polic(?:y|ies)|guardrails?|directives?)\b"
        ),
        "Text directs the agent to discard higher-priority instructions or safeguards, a classic prompt-injection pattern.",
        "Remove the override instruction. Skills should add domain guidance, not replace system or user rules.",
    ),
    Rule(
        "SS-SEC-001", "secret_disclosure", "Instruction to read or disclose secrets/credentials", Severity.high,
        _flags(rf"\b{DISCLOSE_VERB}\b[^.\n]{{0,60}}?{SECRET_TARGET}"),
        "Text asks the agent to access, print or transmit credentials or secret material.",
        "Delete the instruction. If the skill legitimately needs a credential, document it as a user-provided setting and never echo it.",
    ),
    Rule(
        "SS-EXF-001", "data_exfiltration", "Instruction to send data to an external destination", Severity.high,
        _flags(
            r"\b(?:send|post|upload|transmit|forward|exfiltrate|submit|beacon|report|sync)\b[^\n]{0,80}?"
            r"(?P<dest>https?://[^\s<>\"'`)\]]+|\bwebhooks?\b|\bremote\s+(?:server|endpoint)|\bexternal\s+(?:server|endpoint|url)|pastebin)"
        ),
        "Text directs the agent to transmit gathered content to a destination not justified by the skill's purpose.",
        "Remove the outbound transfer or restrict it to an endpoint the user explicitly configures and approves.",
        post=_exfil_post,
    ),
    Rule(
        "SS-CAP-001", "capability_expansion", "Request for broad or dangerous capabilities", Severity.medium,
        _flags(
            r"(?:\b(?:run|execute|exec)\s+(?:arbitrary|any|all|shell|system)\s+(?:shell\s+)?(?:commands?|code|scripts?)\b"
            r"|\bcurl\b[^\n]{0,120}\|\s*(?:ba|z)?sh\b|\bwget\b[^\n]{0,120}\|\s*(?:ba|z)?sh\b|\bsudo\s+\S+|\brm\s+-rf\s+[/~]"
            r"|\bchmod\s+(?:-R\s+)?777\b"
            r"|\b(?:disable|turn\s+off|bypass|skip)\s+(?:the\s+|all\s+|any\s+)?(?:safety|sandbox(?:ing)?|security|guardrails?|confirmations?|permission\s+(?:checks?|prompts?))\b"
            r"|\b(?:full|unrestricted|root|admin(?:istrator)?)\s+(?:access|privileges|permissions)\b)"
        ),
        "Text requests capabilities (shell execution, privilege escalation, disabled safeguards) beyond a typical skill's scope.",
        "Scope the skill to the minimum tools it needs and declare them in frontmatter; never ask to disable safeguards.",
        post=_shell_post,
    ),
    Rule(
        "SS-CNC-001", "concealment", "Instruction to hide actions from the user", Severity.medium,
        _flags(
            r"(?:\b(?:do\s+not|don['’]t|never)\s+(?:tell|inform|mention|reveal\s+this|show\s+this|disclose\s+this|notify)\b[^.\n]{0,25}\buser\b"
            r"|\bwithout\s+(?:telling|informing|notifying|asking|alerting)\s+(?:the\s+)?user\b"
            r"|\b(?:secretly|silently|covertly|quietly)\s+(?:send|upload|read|copy|collect|run|execute|include|add|forward)\b)"
        ),
        "Text asks the agent to keep actions hidden from the user, which undermines human oversight.",
        "Remove concealment language. Agent actions should remain transparent to the user.",
        skip_if_negated=False,
    ),
    Rule(
        "SS-ROLE-001", "role_hijack", "Attempt to redefine the agent's role or system prompt", Severity.medium,
        _flags(
            r"(?:\byou\s+are\s+now\b|\bact\s+as\s+(?:an?\s+|the\s+)?(?:unrestricted|jailbroken|unfiltered|dan)\b|\bdeveloper\s+mode\b"
            r"|\bnew\s+system\s+prompt\b|<\|im_start\|>|\[\s*system\s*\]|^\s*system\s*prompt\s*:)"
        ),
        "Text tries to replace the agent's identity or inject a system-level prompt.",
        "Describe the task instead of redefining the agent's role.",
    ),
    Rule(
        "SS-ENC-002", "encoded_payload", "Reference to decoding hidden instructions", Severity.medium,
        _flags(
            r"\b(?:decode|deobfuscate|unescape|base64[-\s]?decode|rot13)\b[^.\n]{0,40}\b(?:following|below|this|instructions?|payload|string|text)\b"
        ),
        "Text asks the agent to decode content, which can smuggle instructions past reviewers.",
        "Write instructions in plain text so reviewers can see them.",
    ),
]

_B64 = re.compile(r"(?<![A-Za-z0-9+/=])[A-Za-z0-9+/]{40,}={0,2}(?![A-Za-z0-9+/=])")


def _try_b64(s: str) -> Optional[str]:
    try:
        raw = base64.b64decode(s + "=" * (-len(s) % 4), validate=True)
    except (binascii.Error, ValueError):
        return None
    try:
        decoded = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    printable = sum(1 for c in decoded if c.isprintable() or c in "\n\t")
    if not decoded or printable / len(decoded) < 0.95:
        return None
    return decoded


def scan_text(text: str, _depth: int = 0) -> list[RuleMatch]:
    matches: list[RuleMatch] = []
    for rule in RULES:
        for m in rule.pattern.finditer(text):
            s, _ = sentence_bounds(text, m.start(), m.end())
            if rule.skip_if_negated and NEGATION.search(text[s:m.start()]):
                continue
            extra = rule.post(m, text) if rule.post else {}
            if extra is None:
                continue
            severity = extra.pop("severity", rule.severity)
            matches.append(
                RuleMatch(
                    rule_id=rule.rule_id, category=rule.category, title=rule.title, severity=severity,
                    start=m.start(), end=m.end(), rationale=rule.rationale, remediation=rule.remediation,
                    observed=f"Rule {rule.rule_id} matched: “{m.group(0)[:160]}”", extra=extra,
                )
            )

    # Encoded payloads: decode with a documented decoder (RFC 4648 base64, UTF-8, >=95% printable).
    for m in _B64.finditer(text):
        decoded = _try_b64(m.group(0))
        if decoded is None:
            continue
        inner = scan_text(decoded, _depth + 1) if _depth == 0 else []
        severity = Severity.high if inner else Severity.medium
        matches.append(
            RuleMatch(
                rule_id="SS-ENC-001", category="encoded_payload", title="Base64-encoded text payload",
                severity=severity, start=m.start(), end=m.end(),
                rationale="A long base64 string decodes to readable text that reviewers cannot see directly."
                + (" The decoded text itself matches instruction rules: " + ", ".join(sorted({i.rule_id for i in inner})) if inner else ""),
                remediation="Replace encoded content with plain text or remove it.",
                observed="Base64 run of %d chars decodes to %d printable characters." % (len(m.group(0)), len(decoded)),
                decoded_payload=decoded[:500], decoder="base64 (RFC 4648) → UTF-8, accepted when ≥95% printable",
                extra={"inner_rule_ids": sorted({i.rule_id for i in inner})},
            )
        )
    return matches


def instruction_signals(text: str) -> list[str]:
    """Rule IDs that match ``text`` (used to assess hidden/concealed content)."""
    return sorted({m.rule_id for m in scan_text(text)})


def extract_destinations(text: str) -> list[str]:
    return sorted({u.group(0).rstrip(".,;:") for u in URL.finditer(text)})


def extract_sensitive_mentions(text: str) -> list[str]:
    found = set()
    for m in re.finditer(SECRET_TARGET, text, re.IGNORECASE):
        found.add(m.group(0).strip().lower())
    return sorted(found)

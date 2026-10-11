"""Normalize analyzer/model output into the single ``Finding`` schema."""

from __future__ import annotations

import re

from ..analyzers.common import escape_invisibles, excerpt
from ..analyzers.static_rules import RuleMatch
from ..model_adapter.schemas import ModelAnalysis
from ..parser.source_map import SourceMap
from ..schemas import SEVERITY_ORDER, Detector, EvidenceType, Finding, Severity

HIDDEN_RULE_PREFIXES = ("SS-UNI", "SS-HID", "SS-WS")


def _short(rule_id: str) -> str:
    return rule_id.replace("SS-", "")


class FindingBuilder:
    def __init__(self) -> None:
        self.findings: list[Finding] = []
        self._seen: set[tuple] = set()
        self._counter: dict[str, int] = {}

    def _next_id(self, rule_id: str) -> str:
        n = self._counter.get(rule_id, 0) + 1
        self._counter[rule_id] = n
        return f"F-{_short(rule_id)}-{n:03d}"

    def add_match(self, m: RuleMatch, path: str, smap: SourceMap, hidden_regions: list[tuple[int, int, str]]) -> None:
        key = (m.rule_id, path, m.start, m.end)
        if key in self._seen:
            return
        self._seen.add(key)
        ls, cs = smap.position(m.start)
        le, ce = smap.position(max(m.start, m.end - 1))
        is_hidden_detector = m.rule_id.startswith(HIDDEN_RULE_PREFIXES)
        interpretation = m.rationale
        extra = dict(m.extra)
        if not is_hidden_detector:
            region = next((r for r in hidden_regions if r[0] <= m.start < r[1]), None)
            if region:
                extra["inside_hidden_region"] = region[2]
                interpretation += f" This text is inside a {region[2]} and may not be visible in rendered views."
        self.findings.append(Finding(
            finding_id=self._next_id(m.rule_id), rule_id=m.rule_id, category=m.category, severity=m.severity,
            title=m.title, source_file=path, line_start=ls, column_start=cs, line_end=le, column_end=ce + 1,
            evidence=excerpt(smap.text, m.start, m.end, pad=20), observed_fact=m.observed,
            interpretation=interpretation, remediation=m.remediation,
            detector=Detector.unicode_scanner if is_hidden_detector else Detector.static_rules,
            evidence_type=EvidenceType.observed if is_hidden_detector else EvidenceType.rule_based,
            annotation_ids=extra.pop("annotation_ids", []), decoded_payload=m.decoded_payload, decoder=m.decoder,
            extra=extra,
        ))

    def add_parser_problem(self, path: str, problem: str) -> None:
        self.findings.append(Finding(
            finding_id=self._next_id("SS-META-001"), rule_id="SS-META-001", category="metadata",
            severity=Severity.low, title="Skill metadata problem", source_file=path, line_start=1, column_start=1,
            line_end=1, column_end=1, evidence="", observed_fact=problem,
            interpretation="Missing or malformed metadata makes the declared purpose harder to verify.",
            remediation="Add valid YAML frontmatter with 'name' and 'description'.",
            detector=Detector.parser, evidence_type=EvidenceType.observed,
        ))

    def add_purpose_mismatch(self, description: str | None, smap: SourceMap | None) -> None:
        desc = (description or "").lower()
        checks = [
            ("SS-EXF-001", r"network|http|api|upload|send|sync|webhook|remote|server|url",
             "outbound data transfer", "network"),
            ("SS-SEC-001", r"credential|secret|key|token|password|auth|login|env", "credential access", "credentials"),
            ("SS-CAP-001", r"shell|command|terminal|execute|script|admin|devops|system", "shell/privileged execution", "shell"),
        ]
        line = 1
        if smap is not None:
            m = re.search(r"^description\s*:", smap.text, re.M)
            if m:
                line = smap.position(m.start())[0]
        for rule_id, declared_rx, label, cap in checks:
            related = [f for f in self.findings if f.rule_id == rule_id]
            if not related or re.search(declared_rx, desc):
                continue
            self.findings.append(Finding(
                finding_id=self._next_id("SS-PUR-001"), rule_id="SS-PUR-001", category="purpose_mismatch",
                severity=Severity.medium, title=f"Instructions require {label} not mentioned in the description",
                source_file="SKILL.md", line_start=line, column_start=1, line_end=line, column_end=1,
                evidence=escape_invisibles(description or "(no description)", 300),
                observed_fact=f"{len(related)} {rule_id} finding(s) exist, but the declared description never mentions {label}.",
                interpretation="The skill's behaviour appears to exceed its declared purpose.",
                remediation="Either remove the undeclared behaviour or document it explicitly in the description.",
                detector=Detector.static_rules, evidence_type=EvidenceType.rule_based,
                extra={"related_finding_ids": [f.finding_id for f in related], "capability": cap},
            ))

    def add_model_analysis(self, analysis: ModelAnalysis, files: dict[str, str], smaps: dict[str, SourceMap]) -> None:
        for mf in analysis.findings:
            quote = mf.evidence_excerpt.strip()
            path = mf.source_file if mf.source_file in files else next(
                (p for p, t in files.items() if quote and (quote in t or quote in escape_invisibles(t))), mf.source_file)
            text = files.get(path, "")
            pos = text.find(quote) if quote else -1
            verified = pos >= 0
            if not verified and quote and quote in escape_invisibles(text):
                verified = True
                pos = 0
            line, col = (smaps[path].position(pos) if (verified and path in smaps) else (0, 0))
            # Corroborate: attach to an overlapping deterministic finding instead of duplicating.
            overlap = next((f for f in self.findings if verified and f.source_file == path and f.line_start <= line <= f.line_end
                            and f.detector != Detector.model), None)
            if overlap:
                overlap.model_interpretation = f"{mf.title}: {mf.rationale}"
                overlap.model_confidence = mf.confidence
                continue
            sev = Severity(mf.severity)
            if not verified:
                sev = Severity.informational
            elif SEVERITY_ORDER[sev] > SEVERITY_ORDER[Severity.medium]:
                sev = Severity.medium  # model alone cannot assert high severity without deterministic evidence
            self.findings.append(Finding(
                finding_id=self._next_id("SS-MODEL"), rule_id="SS-MODEL", category=mf.category, severity=sev,
                title=mf.title, source_file=path, line_start=line, column_start=col, line_end=line, column_end=col,
                evidence=escape_invisibles(quote, 300),
                observed_fact=("Quoted excerpt found verbatim in source." if verified
                               else "Excerpt NOT found verbatim in source (unverified model quote)."),
                interpretation="Model interpretation (may be wrong).",
                model_interpretation=mf.rationale, model_confidence=mf.confidence,
                remediation="Review the quoted text in context.", detector=Detector.model,
                evidence_type=EvidenceType.model_interpretation,
                extra={"model_severity": mf.severity, "quote_verified": verified},
            ))

    def link_tests(self, tests) -> None:
        by_id = {f.finding_id: f for f in self.findings}
        for t in tests:
            for fid in t.source_finding_ids:
                if fid in by_id and t.test_id not in by_id[fid].related_test_ids:
                    by_id[fid].related_test_ids.append(t.test_id)

    def sorted(self) -> list[Finding]:
        return sorted(self.findings, key=lambda f: (-SEVERITY_ORDER[f.severity], f.source_file, f.line_start, f.column_start))

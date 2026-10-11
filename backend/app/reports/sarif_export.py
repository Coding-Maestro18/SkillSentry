"""SARIF 2.1.0 export and validation for SkillSentry scan reports.

Converts normalized findings into OASIS Static Analysis Results Interchange Format
(SARIF 2.1.0) compatible with code scanning viewers.
"""

from __future__ import annotations

import hashlib
import posixpath
import re
from typing import Any

from ..schemas import Finding, ScanReport, Severity


SEVERITY_TO_SARIF_LEVEL = {
    Severity.high: "error",
    Severity.medium: "warning",
    Severity.low: "note",
    Severity.informational: "note",
}


def _clean_text(s: str) -> str:
    """Sanitize text and redact any potential canary values or control codes."""
    if not s:
        return ""
    # Redact synthetic canaries if any leaked
    redacted = re.sub(r"CANARY_SKILL_[0-9a-fA-F]+", "[CANARY_TOKEN_REDACTED]", s)
    # Remove ASCII control characters except newline and tab
    return "".join(ch for ch in redacted if ch in ("\n", "\r", "\t") or ord(ch) >= 32)


def _location(f: Finding, uri_prefix: str = "") -> dict[str, Any] | None:
    """Physical location for a finding, or None when it has no source file.

    Never invents coordinates: the region is emitted only when a line is known, and
    end coordinates only when they are consistent with the start.
    """
    if not f.source_file or not f.source_file.strip():
        return None
    uri = uri_prefix + posixpath.normpath(f.source_file.replace("\\", "/")).lstrip("/")
    phys: dict[str, Any] = {"artifactLocation": {"uri": uri}}
    if f.line_start > 0:
        region: dict[str, Any] = {"startLine": f.line_start}
        if f.column_start > 0:
            region["startColumn"] = f.column_start
        if f.line_end >= f.line_start:
            region["endLine"] = f.line_end
            if f.column_end > 0 and (f.line_end > f.line_start or f.column_end >= f.column_start):
                region["endColumn"] = f.column_end
        phys["region"] = region
    return {"physicalLocation": phys}


def _fingerprint(f: Finding, uri: str) -> str:
    basis = f"{f.rule_id}|{uri}|{f.line_start}|{f.column_start}|{_clean_text(f.evidence)[:200]}"
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:32]


def _driver(version: str, findings: list[Finding]) -> dict[str, Any]:
    rules: dict[str, dict[str, Any]] = {}
    for f in findings:
        if f.rule_id in rules:
            continue
        rules[f.rule_id] = {
            "id": f.rule_id,
            "name": re.sub(r"[^a-zA-Z0-9_]", "_", f.category or f.rule_id),
            "shortDescription": {"text": _clean_text(f.title)},
            "fullDescription": {"text": _clean_text(f.interpretation or f.title)},
            "defaultConfiguration": {"level": SEVERITY_TO_SARIF_LEVEL.get(f.severity, "warning")},
            "properties": {
                "category": f.category,
                "detector": f.detector.value,
                "remediation": _clean_text(f.remediation),
            },
        }
    return {
        "name": "SkillSentry",
        "version": version or "1.1.0",
        "informationUri": "https://github.com/Coding-Maestro18/SkillSentry",
        "rules": list(rules.values()),
    }


def _result(f: Finding, uri_prefix: str = "", scan_id: str | None = None) -> dict[str, Any]:
    props: dict[str, Any] = {
        "findingId": f.finding_id,
        "category": f.category,
        "detector": f.detector.value,
        "evidenceType": f.evidence_type.value,
        "status": f.status.value,
        "occurrences": f.occurrences,
        "sanitizedEvidence": _clean_text(f.evidence[:300]),
    }
    if scan_id:
        props["scanId"] = scan_id
    if f.model_interpretation:
        props["modelInterpretation"] = _clean_text(f.model_interpretation[:500])
    result: dict[str, Any] = {
        "ruleId": f.rule_id,
        "level": SEVERITY_TO_SARIF_LEVEL.get(f.severity, "warning"),
        "message": {"text": _clean_text(f"{f.title}: {f.observed_fact}")},
        "properties": {"skillSentry": props},
    }
    loc = _location(f, uri_prefix)
    if loc:
        result["locations"] = [loc]
        uri = loc["physicalLocation"]["artifactLocation"]["uri"]
        result["partialFingerprints"] = {"skillSentryFinding/v1": _fingerprint(f, uri)}
    return result


def _document(runs: list[dict[str, Any]]) -> dict[str, Any]:
    return {"$schema": "https://json.schemastore.org/sarif-2.1.0.json", "version": "2.1.0", "runs": runs}


def to_sarif(report: ScanReport) -> dict[str, Any]:
    """Convert a ScanReport into a SARIF 2.1.0 log (paths are relative to the skill package root)."""
    return _document([{
        "tool": {"driver": _driver(report.analyzer_version, report.findings)},
        "results": [_result(f) for f in report.findings],
    }])


def campaign_to_sarif(campaign_id: str, reports: list[ScanReport]) -> dict[str, Any]:
    """Source-anchored findings from every campaign participant.

    Each skill's paths are prefixed with ``skill_a/`` / ``skill_b/`` so files with the
    same name in different packages stay distinct. Simulated traces have no source
    location and are not exported here; they stay in the JSON campaign report.
    """
    findings = [f for r in reports for f in r.findings]
    results = []
    for role, r in zip(("skill_a/", "skill_b/"), reports):
        results += [_result(f, role, r.scan_id) for f in r.findings]
    version = reports[0].analyzer_version if reports else ""
    return _document([{
        "tool": {"driver": _driver(version, findings)},
        "results": results,
        "properties": {"skillSentry": {"campaignId": campaign_id, "scanIds": [r.scan_id for r in reports]}},
    }])


def validate_sarif(data: dict[str, Any]) -> tuple[bool, list[str]]:
    """Local structural validation of SARIF 2.1.0 dictionary without external network calls."""
    errors: list[str] = []

    if data.get("version") != "2.1.0":
        errors.append(f"Expected SARIF version '2.1.0', got '{data.get('version')}'")

    if not isinstance(data.get("runs"), list) or len(data["runs"]) == 0:
        errors.append("SARIF document must contain non-empty 'runs' array")
        return False, errors

    run = data["runs"][0]
    tool = run.get("tool", {})
    driver = tool.get("driver", {})

    if not driver.get("name"):
        errors.append("Tool driver must specify a name")

    if not isinstance(driver.get("rules"), list):
        errors.append("Driver rules must be an array")

    results = run.get("results")
    if not isinstance(results, list):
        errors.append("Run results must be an array")
    else:
        valid_levels = {"error", "warning", "note", "none"}
        for idx, res in enumerate(results):
            if not res.get("ruleId"):
                errors.append(f"Result {idx} is missing 'ruleId'")
            if res.get("level") not in valid_levels:
                errors.append(f"Result {idx} has invalid level: {res.get('level')}")
            if "locations" in res:
                for loc_idx, loc in enumerate(res["locations"]):
                    ploc = loc.get("physicalLocation", {})
                    uri = ploc.get("artifactLocation", {}).get("uri", "")
                    if not uri:
                        errors.append(f"Result {idx} location {loc_idx} missing uri")
                    if uri.startswith("/") or re.match(r"^[A-Za-z]:", uri):
                        errors.append(f"Result {idx} location {loc_idx} uri must be relative, got: {uri}")
                    region = ploc.get("region")
                    if region is not None:
                        start = region.get("startLine", 0)
                        if not isinstance(start, int) or start < 1:
                            errors.append(f"Result {idx} location {loc_idx} has invalid startLine")
                        if region.get("endLine", start) < start:
                            errors.append(f"Result {idx} location {loc_idx} endLine precedes startLine")

    return len(errors) == 0, errors

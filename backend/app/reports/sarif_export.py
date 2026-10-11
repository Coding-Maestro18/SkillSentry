"""SARIF 2.1.0 export and validation for SkillSentry scan reports.

Converts normalized findings into OASIS Static Analysis Results Interchange Format
(SARIF 2.1.0) compatible with code scanning viewers.
"""

from __future__ import annotations

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


def to_sarif(report: ScanReport) -> dict[str, Any]:
    """Convert a ScanReport into a SARIF 2.1.0 compliant JSON dictionary."""
    rules_dict: dict[str, dict[str, Any]] = {}
    sarif_results: list[dict[str, Any]] = []

    for f in report.findings:
        level = SEVERITY_TO_SARIF_LEVEL.get(f.severity, "warning")
        rule_id = f.rule_id

        if rule_id not in rules_dict:
            rules_dict[rule_id] = {
                "id": rule_id,
                "name": re.sub(r"[^a-zA-Z0-9_]", "_", f.category or rule_id),
                "shortDescription": {"text": _clean_text(f.title)},
                "fullDescription": {"text": _clean_text(f.interpretation or f.title)},
                "defaultConfiguration": {"level": level},
                "properties": {
                    "category": f.category,
                    "detector": f.detector.value if hasattr(f.detector, "value") else str(f.detector),
                    "remediation": _clean_text(f.remediation),
                },
            }

        result: dict[str, Any] = {
            "ruleId": rule_id,
            "level": level,
            "message": {
                "text": _clean_text(f"{f.title}: {f.observed_fact}")
            },
            "properties": {
                "skillSentry": {
                    "findingId": f.finding_id,
                    "category": f.category,
                    "detector": f.detector.value if hasattr(f.detector, "value") else str(f.detector),
                    "evidenceType": f.evidence_type.value if hasattr(f.evidence_type, "value") else str(f.evidence_type),
                    "status": f.status.value if hasattr(f.status, "value") else str(f.status),
                    "occurrences": f.occurrences,
                    "sanitizedEvidence": _clean_text(f.evidence[:300]),
                }
            },
        }

        # Source location
        if f.source_file and f.source_file.strip():
            rel_path = posixpath.normpath(f.source_file.replace("\\", "/"))
            loc: dict[str, Any] = {
                "physicalLocation": {
                    "artifactLocation": {
                        "uri": rel_path,
                    },
                    "region": {
                        "startLine": max(1, f.line_start),
                        "startColumn": max(1, f.column_start),
                        "endLine": max(1, f.line_end),
                        "endColumn": max(1, f.column_end),
                    },
                }
            }
            result["locations"] = [loc]

        sarif_results.append(result)

    sarif_doc: dict[str, Any] = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "SkillSentry",
                        "version": report.analyzer_version or "1.1.0",
                        "informationUri": "https://github.com/Coding-Maestro18/SkillSentry",
                        "rules": list(rules_dict.values()),
                    }
                },
                "results": sarif_results,
            }
        ],
    }

    return sarif_doc


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
                    if uri.startswith("/"):
                        errors.append(f"Result {idx} location {loc_idx} uri must be relative, got: {uri}")

    return len(errors) == 0, errors

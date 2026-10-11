"""Capability Passport and report summary."""

from __future__ import annotations

from collections import Counter

from ..schemas import (
    CapabilityPassport,
    FileAnnotation,
    FileEntry,
    Finding,
    ModelInfo,
    ScanSummary,
    Severity,
    TestResult,
)

RULE_CAPABILITY = {
    "SS-SEC-001": "credential / secret access",
    "SS-EXF-001": "outbound network transfer",
    "SS-CAP-001": "shell or privileged execution",
    "SS-OVR-001": "overriding higher-priority instructions",
    "SS-ROLE-001": "redefining the agent's role",
    "SS-CNC-001": "acting without user awareness",
}

LIMITATIONS = [
    "All tool actions are simulated with mock tools; no uploaded code was executed and no real network request was made.",
    "A scan only covers SKILL.md and supported text files under references/; scripts and assets are inventoried but not analysed.",
    "Hidden HTML/CSS detection is regex-based and is not a browser rendering engine.",
    "Whitespace heuristics can miss novel encodings and can flag legitimate formatting.",
    "Confusable detection uses a pinned subset of Unicode confusables data; legitimate multilingual text may need review.",
    "Simulated behaviour does not prove how a particular agent runtime would load or act on these files.",
    "Model interpretations may be wrong; they are labelled separately from deterministic observations.",
    "A clean report does not establish that a skill is safe.",
]


def build_passport(
    skill_name: str | None, description: str | None, declared_tools: list[str], files: list[FileEntry],
    findings: list[Finding], results: list[TestResult], model_caps: list[str], destinations: list[str],
    sensitive: list[str], model: ModelInfo | None,
) -> CapabilityPassport:
    observed = []
    for r in results:
        for e in r.events:
            arg = next(iter(e.sanitized_arguments.values()), "")
            observed.append(f"{e.tool_name}({arg}) → {e.policy_decision.value} [{r.test_id}]")
    unresolved = [f"{f.finding_id}: {f.title} ({f.source_file}:{f.line_start})" for f in findings
                  if f.severity in (Severity.high, Severity.medium) and f.status.value == "needs_review"][:25]
    if model and model.status != "ok":
        unresolved.append(f"Model analysis not available ({model.status}); semantic review not performed.")
    return CapabilityPassport(
        skill_name=skill_name, description=description,
        files_discovered=[f.relative_path for f in files],
        references=[f.relative_path for f in files if f.role == "reference"],
        declared_capabilities=declared_tools,
        inferred_capabilities_model=model_caps,
        inferred_capabilities_rules=sorted({RULE_CAPABILITY[f.rule_id] for f in findings if f.rule_id in RULE_CAPABILITY}),
        observed_simulated_actions=observed,
        sensitive_items_mentioned=sensitive,
        destinations_mentioned=destinations,
        unresolved_concerns=unresolved,
        unscanned_files=[f"{f.relative_path} — {f.skip_reason}" for f in files if not f.scanned],
    )


def build_summary(files: list[FileEntry], findings: list[Finding], annotations: list[FileAnnotation],
                  results: list[TestResult]) -> ScanSummary:
    sev = Counter(f.severity.value for f in findings)
    cat = Counter(f.category for f in findings)
    hidden = Counter(a.annotation_type for a in annotations if a.severity != Severity.informational)
    hidden_info = Counter(a.annotation_type for a in annotations if a.severity == Severity.informational)
    hidden_counts = dict(hidden)
    for k, v in hidden_info.items():
        hidden_counts[f"{k} (likely benign)"] = v
    status = Counter(r.status for r in results)
    scanned = sum(1 for f in files if f.scanned)
    if sev.get("high"):
        headline = f"{sev['high']} high-priority finding(s) need review."
    elif sev.get("medium"):
        headline = f"No high-priority findings; {sev['medium']} medium-priority finding(s) need review."
    else:
        headline = "No high-priority findings detected in this scan (see coverage and limitations)."
    return ScanSummary(
        files_scanned=scanned, files_skipped=len(files) - scanned,
        findings_by_severity={k: sev.get(k, 0) for k in ("high", "medium", "low", "informational")},
        findings_by_category=dict(cat), hidden_content_counts=hidden_counts, tests_total=len(results),
        tests_by_status={k: status.get(k, 0) for k in ("pass", "fail", "needs_review", "skipped")},
        headline=headline,
    )

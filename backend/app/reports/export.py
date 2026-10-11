"""JSON and Markdown export plus before/after comparison."""

from __future__ import annotations

import html
from collections import Counter

from ..analyzers.common import escape_invisibles
from ..schemas import Comparison, ScanReport


def to_json(report: ScanReport) -> dict:
    data = report.model_dump(mode="json")
    # Exports carry escaped evidence only; full file contents are not included by default.
    return data


def _md(s: str) -> str:
    return html.escape(escape_invisibles(s or ""), quote=False).replace("|", "\\|").replace("\n", " ")


def to_markdown(report: ScanReport) -> str:
    out = [f"# SkillSentry report — {_md(report.skill_name or 'unnamed skill')}", ""]
    out += [f"- Scan ID: `{report.scan_id}`" + (f" (revision of `{report.parent_scan_id}`)" if report.parent_scan_id else ""),
            f"- Created: {report.created_at}",
            f"- Analyzer {report.analyzer_version}, ruleset {report.ruleset_version}, suite {report.suite_version}",
            f"- Unicode data {report.unicode_version}; confusables: {report.confusables_version}"]
    if report.model:
        m = report.model
        out.append(f"- Model: {m.name} (rev {m.revision}, license {m.license}) via {m.provider}, mode **{m.inference_mode}**, "
                   f"status **{m.status}** — {_md(m.status_detail)}")
    if report.summary:
        s = report.summary
        out += ["", f"**{_md(s.headline)}**", "",
                f"Files scanned: {s.files_scanned}, skipped: {s.files_skipped}. "
                f"Findings — " + ", ".join(f"{k}: {v}" for k, v in s.findings_by_severity.items()) + ". "
                f"Tests — " + ", ".join(f"{k}: {v}" for k, v in s.tests_by_status.items()) + "."]
    out += ["", "## Files", "", "| Path | Scanned | Note |", "|---|---|---|"]
    for f in report.files:
        out.append(f"| `{_md(f.relative_path)}` | {'yes' if f.scanned else 'no'} | {_md(f.skip_reason or '; '.join(f.warnings))} |")
    out += ["", "## Findings", "", "| ID | Severity | Source | Location | Title | Evidence |", "|---|---|---|---|---|---|"]
    for f in report.findings:
        out.append(f"| {f.finding_id} | {f.severity.value} | {f.evidence_type.value} | `{_md(f.source_file)}:{f.line_start}:{f.column_start}` "
                   f"| {_md(f.title)} | {_md(f.evidence)[:200]} |")
    out += ["", "## Tests", "", "| Test | Name | Origin | Status | Summary |", "|---|---|---|---|---|"]
    names = {t.test_id: t for t in report.tests}
    for r in report.results:
        t = names.get(r.test_id)
        out.append(f"| {r.test_id} | {_md(t.name if t else '')} | {t.origin if t else ''} | **{r.status}** | {_md(r.summary)} |")
    out += ["", "### Trace events", ""]
    for r in report.results:
        for e in r.events:
            out.append(f"- `{e.event_id}` {e.tool_name}({_md(', '.join(f'{k}={v}' for k, v in e.sanitized_arguments.items()))}) "
                       f"→ **{e.policy_decision.value}** — {_md(e.decision_reason)}")
    out += ["", "## Limitations", ""] + [f"- {_md(l)}" for l in report.limitations]
    return "\n".join(out) + "\n"


def _key(f) -> tuple:
    # observed_fact holds the matched text / code points, which survives edits elsewhere in the file
    return (f.rule_id, f.source_file, f.observed_fact)


def compare(original: ScanReport, revised: ScanReport) -> Comparison:
    before = {r.test_id: r for r in original.results}
    after = {r.test_id: r for r in revised.results}
    names = {t.test_id: t.name for t in original.tests}
    rows = []
    improved = regressed = 0
    for tid in [t.test_id for t in original.tests]:
        b, a = before.get(tid), after.get(tid)
        change = "unchanged"
        if b and a and b.status != a.status:
            if a.status == "pass":
                change, improved = "improved", improved + 1
            elif b.status == "pass":
                change, regressed = "regressed", regressed + 1
            else:
                change = "changed"
        if a is None:
            change = "not run"
        rows.append({"test_id": tid, "name": names.get(tid, tid), "before": b.status if b else None,
                     "after": a.status if a else None, "change": change,
                     "after_summary": a.summary if a else "Not run against the revision."})
    bk = {_key(f): f for f in original.findings}
    ak = {_key(f): f for f in revised.findings}
    same_suite = [t.test_id for t in original.tests] == [t.test_id for t in revised.tests] and \
        original.suite_version == revised.suite_version
    still_failing = sum(1 for r in rows if r["after"] in ("fail", "needs_review"))
    if not same_suite:
        verdict = "Suites differ; no improvement can be claimed."
    elif any(r["after"] in (None, "skipped") for r in rows):
        verdict = "Some tests were not run against the revision; improvement is not verified for those tests."
    elif regressed:
        verdict = f"{regressed} test(s) regressed. {improved} improved."
    elif improved and not still_failing:
        verdict = f"{improved} test(s) improved and no tests fail on the revision (same suite, same test IDs)."
    elif improved:
        verdict = f"{improved} test(s) improved; {still_failing} still fail or need review."
    else:
        verdict = "No change in test outcomes."
    return Comparison(
        original_scan_id=original.scan_id, revised_scan_id=revised.scan_id, suite_version=original.suite_version,
        same_suite=same_suite, tests=rows,
        findings_before=dict(Counter(f.severity.value for f in original.findings)),
        findings_after=dict(Counter(f.severity.value for f in revised.findings)),
        resolved_findings=[f"{f.finding_id} {f.title}" for k, f in bk.items() if k not in ak],
        remaining_findings=[f"{f.finding_id} {f.title}" for k, f in ak.items() if k in bk],
        new_findings=[f"{f.finding_id} {f.title}" for k, f in ak.items() if k not in bk],
        verdict=verdict,
    )

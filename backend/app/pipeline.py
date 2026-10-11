"""Scan orchestration: parse → analyze → model → tests → simulate → report."""

from __future__ import annotations

import secrets
import time
import traceback
import logging
from typing import Optional

from .analyzers import static_rules, unicode_hidden_content
from .analyzers.common import UNICODE_VERSION
from .analyzers.confusables import CONFUSABLES_VERSION
from .config import ANALYZER_VERSION, RULESET_VERSION, SUITE_VERSION, Settings
from .harness.runner import run_suite
from .ingest.archive_validator import RawFile
from .ingest.inventory import build_inventory
from .model_adapter.base import AnalysisInput
from .model_adapter.local_model import get_adapter
from .parser.skill_parser import parse_skill
from .parser.source_map import SourceMap
from .persistence.store import ScanStore
from .reports.normalize import FindingBuilder
from .reports.passport import LIMITATIONS, build_passport, build_summary
from .schemas import ScanReport, ScanState, TestCase, utcnow
from .test_generation.generator import build_fixed_suite, build_model_tests

log = logging.getLogger("skillsentry.pipeline")


def new_scan_id() -> str:
    return "scan_" + secrets.token_hex(6)


def create_report(scan_id: str, input_kind: str, parent: Optional[str] = None) -> ScanReport:
    return ScanReport(
        scan_id=scan_id, parent_scan_id=parent, created_at=utcnow(), input_kind=input_kind,  # type: ignore[arg-type]
        status=ScanState.queued, stage_detail="Queued", analyzer_version=ANALYZER_VERSION,
        ruleset_version=RULESET_VERSION, unicode_version=UNICODE_VERSION, confusables_version=CONFUSABLES_VERSION,
        suite_version=SUITE_VERSION, limitations=LIMITATIONS,
    )


def run_pipeline(
    report: ScanReport, raw_files: list[RawFile], store: ScanStore, settings: Settings,
    reuse_suite: Optional[list[TestCase]] = None,
) -> ScanReport:
    timings: dict[str, int] = {}

    def stage(state: ScanState, detail: str) -> None:
        report.status = state
        report.stage_detail = detail
        store.save(report)
        log.info("scan %s → %s", report.scan_id, state.value)

    try:
        t0 = time.monotonic()
        stage(ScanState.parsing, "Building file inventory and parsing SKILL.md")
        inv = build_inventory(raw_files, settings)
        report.files = inv.entries
        files = {t.path: t.text for t in inv.texts}
        store.save_files(report.scan_id, files)
        smaps = {t.path: SourceMap(t.text) for t in inv.texts}
        builder = FindingBuilder()
        skill_text = files.get("SKILL.md")
        declared_tools: list[str] = []
        if skill_text is None:
            builder.add_parser_problem("SKILL.md", "No SKILL.md found; generic text scan only.")
        else:
            parsed = parse_skill(skill_text)
            report.frontmatter = parsed.frontmatter
            report.skill_name = parsed.name
            report.skill_description = parsed.description
            declared_tools = parsed.declared_tools
            for p in parsed.problems:
                builder.add_parser_problem("SKILL.md", p)
        timings["parse"] = int((time.monotonic() - t0) * 1000)

        t1 = time.monotonic()
        stage(ScanState.analyzing, "Running deterministic rules and hidden-content scanner")
        hidden_snippets: list[dict] = []
        for tf in inv.texts:
            anns, hidden_matches = unicode_hidden_content.scan_file(tf.file_id, tf.path, tf.text, smaps[tf.path])
            report.annotations.extend(anns)
            regions = [(a.start_offset, a.end_offset, "HTML comment" if a.annotation_type == "html_comment" else "hidden HTML element")
                       for a in anns if a.annotation_type in ("html_comment", "hidden_html")]
            for m in hidden_matches:
                builder.add_match(m, tf.path, smaps[tf.path], regions)
                content = m.extra.get("hidden_content") or m.decoded_payload
                if content:
                    hidden_snippets.append({"kind": m.rule_id, "file": tf.path,
                                            "line": smaps[tf.path].position(m.start)[0], "content": content})
            for m in static_rules.scan_text(tf.text):
                builder.add_match(m, tf.path, smaps[tf.path], regions)
        builder.add_purpose_mismatch(report.skill_description, smaps.get("SKILL.md"))
        timings["deterministic"] = int((time.monotonic() - t1) * 1000)

        t2 = time.monotonic()
        stage(ScanState.analyzing, "Open-weight model analysis (untrusted content, no tools)")
        adapter = get_adapter(settings)
        result = adapter.analyze_skill(AnalysisInput(
            skill_name=report.skill_name, description=report.skill_description, files=files,
            hidden_content=hidden_snippets,
            rule_summary=[f"- {f.rule_id} {f.source_file}:{f.line_start} {f.title}" for f in builder.findings],
        ))
        report.model = result.info
        model_caps: list[str] = []
        hypotheses = []
        if result.analysis:
            builder.add_model_analysis(result.analysis, files, smaps)
            model_caps = result.analysis.inferred_capabilities
            hypotheses = result.analysis.test_hypotheses
        timings["model"] = int((time.monotonic() - t2) * 1000)

        stage(ScanState.generating_tests, "Building and validating the scenario suite")
        findings_now = builder.sorted()
        if reuse_suite is not None:
            tests = reuse_suite  # identical IDs, versions and frozen arguments
            rejected: list[TestCase] = []
        else:
            tests = build_fixed_suite(findings_now, files)
            model_valid, rejected = build_model_tests(hypotheses, files)
            tests = tests + model_valid
        report.tests = tests
        report.rejected_tests = rejected
        builder.link_tests(tests)

        t3 = time.monotonic()
        stage(ScanState.simulating, "Running scenarios against mock tools")
        report.findings = builder.sorted()
        report.results = run_suite(tests, files, report.findings)
        canary_counts = {k: 0 for k in ("matched", "not_observed", "not_evaluable", "blocked_before_send", "not_attempted")}
        for r in report.results:
            if r.canary_event:
                canary_counts[r.canary_event.status] += 1
        report.extensions["canary_summary"] = canary_counts
        report.extensions["sarif"] = {"supported": True, "version": "2.1.0"}
        timings["simulate"] = int((time.monotonic() - t3) * 1000)

        stage(ScanState.reporting, "Building report and capability passport")
        corpus = "\n".join(files.values())
        report.passport = build_passport(
            report.skill_name, report.skill_description, declared_tools, report.files, report.findings,
            report.results, model_caps, static_rules.extract_destinations(corpus),
            static_rules.extract_sensitive_mentions(corpus), report.model,
        )
        report.summary = build_summary(report.files, report.findings, report.annotations, report.results)
        timings["total"] = int((time.monotonic() - t0) * 1000)
        report.timings_ms = timings
        stage(ScanState.completed, "Scan complete")
    except Exception as exc:  # noqa: BLE001 - convert to a reportable failure without leaking internals
        log.error("scan %s failed: %s\n%s", report.scan_id, exc, traceback.format_exc())
        report.status = ScanState.failed
        report.error = {"code": "PIPELINE_ERROR", "message": f"Scan failed during '{report.stage_detail}'.",
                        "details": {"exception": type(exc).__name__}}
        store.save(report)
    return report

import { useState } from "react";
import { api } from "../api/client";
import AttackLab from "../components/AttackLab";
import CapabilityPassport from "../components/CapabilityPassport";
import FindingList from "../components/FindingList";
import FixCompare from "../components/FixCompare";
import ForensicViewer from "../components/ForensicViewer";
import type { ScanReport, TestResult } from "../types";

type Tab = "overview" | "findings" | "source" | "lab" | "fix";

const TABS: { id: Tab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "findings", label: "Findings" },
  { id: "source", label: "Forensic viewer" },
  { id: "lab", label: "Attack lab" },
  { id: "fix", label: "Fix & compare" },
];

export default function ReportPage({ report, onUpdate, onOpenScan }: {
  report: ScanReport;
  onUpdate: (r: ScanReport) => void;
  onOpenScan: (id: string) => void;
}) {
  const [tab, setTab] = useState<Tab>("overview");
  const [target, setTarget] = useState<{ path: string; line: number } | null>(null);
  const [focusTest, setFocusTest] = useState<string | null>(null);

  const onResult = (r: TestResult) =>
    onUpdate({ ...report, results: report.results.map((x) => (x.test_id === r.test_id ? r : x)) });

  return (
    <div className="stack">
      <div className="report-head">
        <div>
          <h2>{report.skill_name ?? "Unnamed skill"}</h2>
          <p className="muted">
            {report.scan_id} · {new Date(report.created_at).toLocaleString()} · input: {report.input_kind}
            {report.parent_scan_id && <> · revision of <button className="link" onClick={() => onOpenScan(report.parent_scan_id!)}>{report.parent_scan_id}</button></>}
          </p>
          {report.model && report.model.status !== "ok" && (
            <p className="banner">Model unavailable — static analysis only ({report.model.status}).</p>
          )}
        </div>
        <div className="row">
          <a className="button secondary" href={api.exportUrl(report.scan_id, "json")}>Export JSON</a>
          <a className="button secondary" href={api.exportUrl(report.scan_id, "markdown")}>Export Markdown</a>
        </div>
      </div>
      <nav className="tabs" role="tablist">
        {TABS.map((t) => (
          <button key={t.id} role="tab" aria-selected={tab === t.id} className={tab === t.id ? "on" : ""} onClick={() => setTab(t.id)}>
            {t.label}
            {t.id === "findings" && <span className="count">{report.findings.length}</span>}
            {t.id === "lab" && <span className="count">{report.tests.length}</span>}
          </button>
        ))}
      </nav>
      {tab === "overview" && <CapabilityPassport report={report} />}
      {tab === "findings" && (
        <FindingList
          report={report}
          onShowSource={(path, line) => { setTarget({ path, line }); setTab("source"); }}
          onShowTest={(t) => { setFocusTest(t); setTab("lab"); }}
        />
      )}
      {tab === "source" && <ForensicViewer report={report} target={target} />}
      {tab === "lab" && <AttackLab report={report} focusTest={focusTest} onResult={onResult} />}
      {tab === "fix" && <FixCompare report={report} onOpenScan={onOpenScan} />}
    </div>
  );
}

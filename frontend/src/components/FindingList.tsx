import { useMemo, useState } from "react";
import type { Finding, ScanReport } from "../types";
import { Card, EvidenceTag, SeverityBadge } from "./ui";

interface Props {
  report: ScanReport;
  onShowSource: (path: string, line: number) => void;
  onShowTest: (testId: string) => void;
}

const ALL = "all";

export default function FindingList({ report, onShowSource, onShowTest }: Props) {
  const [sev, setSev] = useState(ALL);
  const [cat, setCat] = useState(ALL);
  const [file, setFile] = useState(ALL);
  const [ev, setEv] = useState(ALL);
  const [selected, setSelected] = useState<string | null>(report.findings[0]?.finding_id ?? null);

  const options = useMemo(() => ({
    cats: [...new Set(report.findings.map((f) => f.category))].sort(),
    files: [...new Set(report.findings.map((f) => f.source_file))].sort(),
    evs: [...new Set(report.findings.map((f) => f.evidence_type))].sort(),
  }), [report]);

  const shown = report.findings.filter(
    (f) => (sev === ALL || f.severity === sev) && (cat === ALL || f.category === cat) &&
      (file === ALL || f.source_file === file) && (ev === ALL || f.evidence_type === ev),
  );
  const current = report.findings.find((f) => f.finding_id === selected) ?? null;

  return (
    <div className="split">
      <div>
        <div className="filters">
          <Select label="Severity" value={sev} onChange={setSev} options={["high", "medium", "low", "informational"]} />
          <Select label="Category" value={cat} onChange={setCat} options={options.cats} />
          <Select label="File" value={file} onChange={setFile} options={options.files} />
          <Select label="Evidence" value={ev} onChange={setEv} options={options.evs} />
        </div>
        <p className="muted">{shown.length} of {report.findings.length} findings</p>
        <ul className="finding-list" role="listbox" aria-label="Findings">
          {shown.map((f) => (
            <li key={f.finding_id}>
              <button
                className={`finding-row ${selected === f.finding_id ? "active" : ""}`}
                onClick={() => setSelected(f.finding_id)}
                aria-selected={selected === f.finding_id}
                role="option"
              >
                <SeverityBadge severity={f.severity} />
                <span className="fr-title">{f.title}</span>
                <span className="fr-loc">{f.source_file}:{f.line_start}</span>
              </button>
            </li>
          ))}
        </ul>
      </div>
      <div>{current ? <FindingDetail f={current} onShowSource={onShowSource} onShowTest={onShowTest} /> : <p>Select a finding.</p>}</div>
    </div>
  );
}

function Select({ label, value, onChange, options }: { label: string; value: string; onChange: (v: string) => void; options: string[] }) {
  return (
    <label className="field inline">
      <span>{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        <option value={ALL}>all</option>
        {options.map((o) => (
          <option key={o} value={o}>{o}</option>
        ))}
      </select>
    </label>
  );
}

function FindingDetail({ f, onShowSource, onShowTest }: { f: Finding; onShowSource: Props["onShowSource"]; onShowTest: Props["onShowTest"] }) {
  const skeleton = typeof f.extra.skeleton === "string" ? f.extra.skeleton : null;
  const hidden = typeof f.extra.hidden_content === "string" ? f.extra.hidden_content : null;
  return (
    <Card
      title={<>{f.finding_id}: {f.title}</>}
      actions={f.line_start > 0 && <button className="secondary" onClick={() => onShowSource(f.source_file, f.line_start)}>View in source →</button>}
    >
      <div className="row wrap">
        <SeverityBadge severity={f.severity} />
        <EvidenceTag type={f.evidence_type} />
        <span className="tag">{f.rule_id}</span>
        <span className="tag">{f.category}</span>
        <span className="tag">status: {f.status.replace("_", " ")}</span>
      </div>
      <dl className="kv">
        <dt>Location</dt>
        <dd><code>{f.source_file}:{f.line_start}:{f.column_start}</code>{f.line_end !== f.line_start && <> – {f.line_end}:{f.column_end}</>}</dd>
        <dt>Evidence (escaped)</dt><dd><pre className="evidence">{f.evidence || "—"}</pre></dd>
        <dt>Observed</dt><dd>{f.observed_fact}</dd>
        <dt>Why it matters</dt><dd>{f.interpretation}</dd>
        {hidden && (<><dt>Hidden content</dt><dd><pre className="evidence">{hidden}</pre><p className="note">Present in source and potentially hidden in rendered views; actual exposure depends on the skill loader/runtime.</p></dd></>)}
        {skeleton && (<><dt>Comparison skeleton</dt><dd><code>{skeleton}</code> <span className="muted">(analysis aid only — not the source text)</span></dd></>)}
        {f.decoded_payload && (<><dt>Decoded payload</dt><dd><pre className="evidence">{f.decoded_payload}</pre><span className="muted">Decoder: {f.decoder}</span></dd></>)}
        {f.model_interpretation && (
          <><dt>Model interpretation <span className="tag ev-model_interpretation">model</span></dt>
            <dd>{f.model_interpretation}{f.model_confidence && <span className="muted"> (model-estimated confidence: {f.model_confidence}; not calibrated)</span>}</dd></>
        )}
        <dt>Suggested action</dt><dd>{f.remediation || "Review in context."}</dd>
        <dt>Detector</dt><dd>{f.detector}</dd>
        <dt>Related tests</dt>
        <dd>
          {f.related_test_ids.length
            ? f.related_test_ids.map((t) => <button key={t} className="link" onClick={() => onShowTest(t)}>{t}</button>)
            : <span className="muted">none</span>}
        </dd>
      </dl>
    </Card>
  );
}

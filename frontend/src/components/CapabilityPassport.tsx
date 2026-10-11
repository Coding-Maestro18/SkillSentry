import type { ScanReport } from "../types";
import { Card, List } from "./ui";

export default function CapabilityPassport({ report }: { report: ScanReport }) {
  const p = report.passport;
  const s = report.summary;
  const m = report.model;
  if (!p || !s) return null;
  return (
    <div className="stack">
      <div className={`headline ${s.findings_by_severity.high ? "hl-high" : s.findings_by_severity.medium ? "hl-medium" : "hl-none"}`}>
        {s.headline}
      </div>

      <div className="stat-row">
        {(["high", "medium", "low", "informational"] as const).map((k) => (
          <div key={k} className={`stat sev-${k}`}>
            <div className="stat-n">{s.findings_by_severity[k] ?? 0}</div>
            <div className="stat-l">{k} findings</div>
          </div>
        ))}
        <div className="stat">
          <div className="stat-n">{s.tests_by_status.fail ?? 0}/{s.tests_total}</div>
          <div className="stat-l">tests failing</div>
        </div>
        <div className="stat">
          <div className="stat-n">{s.files_scanned}/{s.files_scanned + s.files_skipped}</div>
          <div className="stat-l">files scanned</div>
        </div>
      </div>

      <div className="grid two">
        <Card title="Capability Passport">
          <dl className="kv">
            <dt>Declared name</dt><dd>{p.skill_name ?? <em className="muted">missing</em>}</dd>
            <dt>Declared description</dt><dd>{p.description ?? <em className="muted">missing</em>}</dd>
            <dt>Declared tools</dt><dd><List items={p.declared_capabilities} empty="None declared" /></dd>
            <dt>Inferred by rules</dt><dd><List items={p.inferred_capabilities_rules} empty="None" /></dd>
            <dt>Inferred by model <span className="tag ev-model_interpretation">model</span></dt>
            <dd><List items={p.inferred_capabilities_model} empty={m?.status === "ok" ? "None" : "Model unavailable"} /></dd>
            <dt>Observed in simulation <span className="tag ev-simulated">simulated</span></dt>
            <dd><List items={p.observed_simulated_actions} empty="No simulated actions" /></dd>
            <dt>Sensitive items mentioned</dt><dd><List items={p.sensitive_items_mentioned} /></dd>
            <dt>Destinations mentioned</dt><dd><List items={p.destinations_mentioned} /></dd>
          </dl>
          <p className="note">
            Observed actions come from the mock harness; they do not mean the skill has access to real tools.
          </p>
        </Card>

        <div className="stack">
          <Card title="Unresolved concerns">
            <List items={p.unresolved_concerns} empty="No medium/high findings awaiting review." />
          </Card>
          <Card title="Hidden-content detector counts">
            <List items={Object.entries(s.hidden_content_counts).map(([k, v]) => `${k}: ${v}`)} empty="Nothing detected" />
          </Card>
          <Card title="Files">
            <table className="table">
              <thead><tr><th>Path</th><th>Scanned</th><th>Note</th></tr></thead>
              <tbody>
                {report.files.map((f) => (
                  <tr key={f.file_id}>
                    <td><code>{f.relative_path}</code></td>
                    <td>{f.scanned ? "✓ yes" : "– no"}</td>
                    <td className="muted">{f.skip_reason ?? (f.warnings.join("; ") || `${f.encoding ?? ""} ${f.line_ending ?? ""}`)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </div>
      </div>

      <div className="grid two">
        <Card title="Provenance">
          <dl className="kv">
            <dt>Model</dt>
            <dd>
              {m ? `${m.name} · rev ${m.revision} · ${m.license} · ${m.provider} (${m.inference_mode})` : "n/a"}
            </dd>
            <dt>Model status</dt><dd>{m ? `${m.status} — ${m.status_detail}` : "n/a"}</dd>
            <dt>Schema-valid model responses</dt><dd>{m ? `${m.schema_valid_responses}/${m.total_responses}` : "n/a"}</dd>
            <dt>Analyzer / ruleset</dt><dd>{report.analyzer_version} / {report.ruleset_version}</dd>
            <dt>Unicode data</dt><dd>{report.unicode_version}</dd>
            <dt>Confusables</dt><dd>{report.confusables_version}</dd>
            <dt>Test suite</dt><dd>{report.suite_version}</dd>
            <dt>Timings (ms)</dt><dd>{Object.entries(report.timings_ms).map(([k, v]) => `${k} ${v}`).join(" · ")}</dd>
          </dl>
        </Card>
        <Card title="Limitations">
          <List items={report.limitations} />
        </Card>
      </div>
    </div>
  );
}

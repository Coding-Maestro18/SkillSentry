import { useState } from "react";
import { api, waitForScan } from "../api/client";
import type { Comparison, FixSuggestion, ScanReport } from "../types";
import { Card, ErrorBox, List, StatusBadge } from "./ui";

interface Props {
  report: ScanReport;
  onOpenScan: (id: string) => void;
}

export default function FixCompare({ report, onOpenScan }: Props) {
  const [fix, setFix] = useState<FixSuggestion | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [useModel, setUseModel] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cmp, setCmp] = useState<Comparison | null>(null);

  async function suggest() {
    setBusy("Requesting fix suggestion…");
    setError(null);
    try {
      const f = await api.fix(report.scan_id, useModel);
      setFix(f);
      setDrafts({ ...f.revised_files });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  async function rerun() {
    setBusy("Rerunning the same test suite against the revised copy…");
    setError(null);
    setCmp(null);
    try {
      const s = await api.rerun(report.scan_id, drafts);
      const done = await waitForScan(s.scan_id, (st) => setBusy(`Revision scan: ${st.stage_detail}`));
      if (done.status === "failed") throw new Error(done.error?.message ?? "Revision scan failed");
      setCmp(await api.comparison(s.scan_id));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  if (report.parent_scan_id) {
    return (
      <Card title="This scan is a revision">
        <p>It reran suite {report.suite_version} from <button className="link" onClick={() => onOpenScan(report.parent_scan_id!)}>{report.parent_scan_id}</button>.</p>
      </Card>
    );
  }

  return (
    <div className="stack">
      <Card
        title="Suggested fix"
        actions={
          <>
            <label className="check"><input type="checkbox" checked={useModel} onChange={(e) => setUseModel(e.target.checked)} /> use model if available</label>
            <button onClick={suggest} disabled={!!busy}>Suggest fix</button>
          </>
        }
      >
        <p className="note">The original upload is never modified. Suggestions apply to an editable copy that you review before rerunning.</p>
        <ErrorBox error={error} />
        {busy && <p className="muted" aria-live="polite">{busy}</p>}
        {fix && (
          <>
            <p>
              <span className={`tag ${fix.origin === "model" ? "ev-model_interpretation" : "ev-rule_based"}`}>
                {fix.origin === "model" ? "Model-proposed fix" : "Deterministic rule-based fix"}
              </span>{" "}
              <span className="muted">{fix.model_status}</span>
            </p>
            <List items={fix.rationale} />
            {Object.keys(fix.diffs).length === 0 && <p className="muted">No changes proposed.</p>}
            {Object.entries(fix.diffs).map(([path, diff]) => (
              <div key={path} className="stack">
                <h4><code>{path}</code></h4>
                <pre className="diff">
                  {diff.split("\n").map((l, i) => (
                    <div key={i} className={l.startsWith("+") && !l.startsWith("+++") ? "add" : l.startsWith("-") && !l.startsWith("---") ? "del" : ""}>
                      {l}
                    </div>
                  ))}
                </pre>
                <label className="field">
                  <span>Revised copy of {path} (editable)</span>
                  <textarea rows={10} spellCheck={false} value={drafts[path] ?? ""} onChange={(e) => setDrafts({ ...drafts, [path]: e.target.value })} />
                </label>
              </div>
            ))}
            {Object.keys(drafts).length > 0 && (
              <button onClick={rerun} disabled={!!busy}>Rerun same suite on revised copy</button>
            )}
          </>
        )}
      </Card>

      {cmp && (
        <Card
          title="Before / after (same test IDs)"
          actions={<button className="secondary" onClick={() => onOpenScan(cmp.revised_scan_id)}>Open revision report →</button>}
        >
          <p className="headline hl-none">{cmp.verdict}</p>
          <p className="muted">Suite {cmp.suite_version} · same suite: {cmp.same_suite ? "yes" : "NO"}</p>
          <table className="table">
            <thead><tr><th>Test</th><th>Before</th><th>After</th><th>Change</th><th>After summary</th></tr></thead>
            <tbody>
              {cmp.tests.map((t) => (
                <tr key={t.test_id}>
                  <td>{t.test_id} · {t.name}</td>
                  <td><StatusBadge status={t.before} /></td>
                  <td><StatusBadge status={t.after} /></td>
                  <td>{t.change}</td>
                  <td className="small">{t.after_summary}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="grid three">
            <div><h4>Resolved findings ({cmp.resolved_findings.length})</h4><List items={cmp.resolved_findings} /></div>
            <div><h4>Remaining ({cmp.remaining_findings.length})</h4><List items={cmp.remaining_findings} /></div>
            <div><h4>New ({cmp.new_findings.length})</h4><List items={cmp.new_findings} /></div>
          </div>
        </Card>
      )}
    </div>
  );
}

import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import type { ScanReport, TestCase, TestResult } from "../types";
import { Card, DecisionBadge, ErrorBox, StatusBadge } from "./ui";

interface Props {
  report: ScanReport;
  focusTest: string | null;
  onResult: (r: TestResult) => void;
}

export default function AttackLab({ report, focusTest, onResult }: Props) {
  const results = Object.fromEntries(report.results.map((r) => [r.test_id, r]));
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const refs = useRef<Record<string, HTMLDivElement | null>>({});

  useEffect(() => {
    if (focusTest) refs.current[focusTest]?.scrollIntoView({ block: "start", behavior: "smooth" });
  }, [focusTest]);

  async function run(t: TestCase) {
    setBusy(t.test_id);
    setError(null);
    try {
      onResult(await api.runTest(report.scan_id, t.test_id));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="stack">
      <p className="note">
        Simulated behavior via mock tools — the harness never executes uploaded code, opens sockets or reads real files.
        A test <strong>fails</strong> when the skill text induces an action the policy gate blocks. Suite {report.suite_version}.
      </p>
      <ErrorBox error={error} />
      {report.tests.map((t) => {
        const r = results[t.test_id];
        return (
          <div key={t.test_id} ref={(el) => { refs.current[t.test_id] = el; }}>
            <Card
              title={<>{t.test_id} · {t.name}</>}
              actions={
                <>
                  <StatusBadge status={r?.status ?? null} />
                  <button className="secondary" disabled={busy === t.test_id} onClick={() => run(t)}>
                    {busy === t.test_id ? "Running…" : "Run again"}
                  </button>
                </>
              }
            >
              <div className={`test-body ${focusTest === t.test_id ? "focus" : ""}`}>
                <div className="row wrap">
                  <span className="tag">{t.kind.replace("_", " ")}</span>
                  <span className={`tag ${t.origin === "model_proposed" ? "ev-model_interpretation" : ""}`}>
                    {t.origin === "model_proposed" ? "model-proposed (validated)" : "fixed suite"}
                  </span>
                  <span className="tag">trigger: {t.trigger.type}{t.trigger.rule_ids.length ? ` ${t.trigger.rule_ids.join(", ")}` : ""}</span>
                </div>
                <p>{t.purpose}</p>
                {t.trigger.excerpt && <p className="muted">Trigger excerpt: <code>{t.trigger.excerpt}</code></p>}
                <table className="table">
                  <thead><tr><th>#</th><th>Mock tool call</th><th>Expected</th><th>Observed</th><th>Reason / mock result</th></tr></thead>
                  <tbody>
                    {t.tool_sequence.map((c, i) => {
                      const ev = r?.events[i];
                      return (
                        <tr key={i}>
                          <td>{i + 1}</td>
                          <td><code>{c.tool}({Object.entries(c.args).map(([k, v]) => `${k}=${JSON.stringify(v)}`).join(", ")})</code></td>
                          <td><DecisionBadge decision={t.expected_policy_decisions[i]} /></td>
                          <td>{ev ? <DecisionBadge decision={ev.policy_decision} /> : <span className="muted">not triggered</span>}</td>
                          <td className="small">{ev ? <>{ev.decision_reason}<br /><span className="muted">{ev.mock_result_summary}</span></> : "—"}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
                {r && <p><strong>Result:</strong> {r.summary}</p>}
                <p className="muted small">Expected outcome: {t.expected_outcome}</p>
              </div>
            </Card>
          </div>
        );
      })}
      {report.rejected_tests.length > 0 && (
        <Card title={`Rejected model-proposed tests (${report.rejected_tests.length})`}>
          <ul className="plain-list">
            {report.rejected_tests.map((t) => (
              <li key={t.test_id}><strong>{t.name}</strong> — {t.validation_notes.join(" ")}</li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}

import React, { useState, useRef, useEffect } from "react";
import { Play, Terminal, Flame, RotateCw, StopCircle, Repeat } from "lucide-react";
import { api } from "../api/client";
import { Card, DecisionBadge, StatusBadge, ErrorAlert } from "./CommonUI";

const CANARY_LABEL = {
  matched: "Canary matched in mock payload",
  blocked_before_send: "Outbound blocked before send",
  not_observed: "Canary not observed",
  not_evaluable: "Canary not evaluable",
  not_attempted: "No outbound attempt",
};

export function CanaryNote({ event }) {
  if (!event) return null;
  const cls =
    event.status === "matched"
      ? "border-rose-500/40 text-rose-300"
      : event.status === "blocked_before_send"
      ? "border-amber-500/40 text-amber-300"
      : "border-slate-700 text-slate-400";
  return (
    <div className={`text-[11px] border rounded-md px-2.5 py-1.5 ${cls}`}>
      <strong>{CANARY_LABEL[event.status] || event.status}</strong>
      {event.source_trace_event_id && <> · source {event.source_trace_event_id}</>}
      {event.sink_trace_event_id && <> · sink {event.sink_trace_event_id}</>}
      <span className="text-slate-500"> · synthetic token, mock payload only (digest {event.token_digest})</span>
    </div>
  );
}

function TraceTable({ calls, events, expected }) {
  return (
    <div className="overflow-x-auto border border-slate-800 rounded-lg">
      <table className="w-full text-left border-collapse text-xs">
        <thead>
          <tr className="bg-[#0b101d] text-slate-400 border-b border-slate-800">
            <th className="py-1.5 px-3 font-medium">#</th>
            <th className="py-1.5 px-3 font-medium">Tool</th>
            <th className="py-1.5 px-3 font-medium">Arguments</th>
            <th className="py-1.5 px-3 font-medium">Decision</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800/60">
          {calls.map((call, idx) => {
            const ev = events?.[idx];
            const args = ev ? ev.sanitized_arguments : call.args;
            return (
              <tr key={idx}>
                <td className="py-1.5 px-3 text-slate-500 font-mono">{idx + 1}</td>
                <td className="py-1.5 px-3 font-mono text-blue-400">{call.tool}</td>
                <td className="py-1.5 px-3 font-mono text-[11px] text-slate-300">
                  {Object.entries(args || {}).map(([k, v]) => (
                    <div key={k}><span className="text-slate-500">{k}:</span> {v}</div>
                  ))}
                </td>
                <td className="py-1.5 px-3">
                  {ev ? (
                    <div className="flex flex-col gap-0.5">
                      <DecisionBadge decision={ev.policy_decision} />
                      <span className="text-[10px] text-slate-500">{ev.decision_reason}</span>
                    </div>
                  ) : (
                    <span className="text-slate-500 text-[11px]">expected {expected?.[idx]}</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

const CANDIDATE_CLS = {
  passed: "text-emerald-300 border-emerald-500/40",
  failed: "text-rose-300 border-rose-500/40",
  needs_review: "text-amber-300 border-amber-500/40",
  rejected: "text-slate-400 border-slate-600 line-through decoration-slate-600",
  skipped: "text-slate-400 border-slate-600",
};

function AdaptivePanel({ scanId }) {
  const [run, setRun] = useState(null);
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let live = true;
    api.listRedTeamRuns(scanId)
      .then((runs) => live && runs.length && setRun(runs[runs.length - 1]))
      .catch(() => {});
    return () => { live = false; };
  }, [scanId]);

  const act = async (label, fn) => {
    setBusy(label);
    setError(null);
    try {
      setRun(await fn());
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(null);
    }
  };

  const m = run?.metrics || {};
  const active = run && (run.status === "running" || run.status === "ready");

  return (
    <Card
      title="Adaptive red team"
      subtitle="Bounded follow-up tests, validated before they run in the mock harness"
      icon={Flame}
      actions={
        <div className="flex items-center gap-2">
          {active && (
            <>
              <button type="button" disabled={!!busy}
                onClick={() => act("advance", () => api.advanceRedTeamRound(run.run_id))}
                className="inline-flex items-center gap-1.5 px-3 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded-md text-xs cursor-pointer disabled:opacity-50">
                <RotateCw size={12} className={busy === "advance" ? "animate-spin" : ""} />
                Next round ({run.current_round + 1}/{run.max_rounds})
              </button>
              <button type="button" disabled={!!busy}
                onClick={() => act("stop", () => api.stopRedTeamRun(run.run_id))}
                className="inline-flex items-center gap-1.5 px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-md text-xs cursor-pointer">
                <StopCircle size={12} /> Stop
              </button>
            </>
          )}
          {run && !active && (m.tests_executed || 0) > 0 && (
            <button type="button" disabled={!!busy}
              onClick={() => act("rerun", () => api.rerunRedTeam(run.run_id))}
              title="Re-run accepted candidates from their saved definitions (no model call)"
              className="inline-flex items-center gap-1.5 px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-md text-xs cursor-pointer disabled:opacity-50">
              <Repeat size={12} /> Re-run accepted
            </button>
          )}
          {(!run || !active) && (
            <button type="button" disabled={!!busy}
              onClick={() => act("start", () => api.startRedTeam(scanId))}
              className="inline-flex items-center gap-1.5 px-3 py-1 bg-rose-600 hover:bg-rose-500 text-white rounded-md text-xs font-semibold cursor-pointer disabled:opacity-50">
              <Flame size={12} /> {busy === "start" ? "Starting…" : run ? "New run" : "Start"}
            </button>
          )}
        </div>
      }
    >
      <ErrorAlert message={error} onClose={() => setError(null)} />
      {!run ? (
        <p className="text-xs text-slate-400 m-0">
          Up to 3 rounds × 3 candidates, at most 9 executed. Unknown tools, URLs and shell-like arguments are rejected
          server-side and never run.
        </p>
      ) : (
        <div className="space-y-3 text-xs">
          <div className="flex flex-wrap gap-x-5 gap-y-1 text-slate-400">
            <span>Status <strong className="text-slate-200">{run.status}</strong></span>
            <span>Round <strong className="text-slate-200">{run.current_round}/{run.max_rounds}</strong></span>
            <span>Executed <strong className="text-slate-200">{m.tests_executed || 0}/{run.max_tests_total}</strong></span>
            <span>
              Results <strong className="text-slate-200">
                {m.tests_passed || 0} pass · {m.tests_failed || 0} fail · {m.tests_needs_review || 0} review
              </strong>
            </span>
            <span>Rejected <strong className="text-slate-200">{m.candidates_rejected || 0}</strong></span>
            <span>
              Benign controls{" "}
              <strong className={run.benign_control_passed ? "text-emerald-400" : "text-rose-400"}>
                {m.benign_controls_passed || 0}/{m.benign_controls_run || 0} pass
              </strong>
            </span>
          </div>
          <div className="text-slate-500">
            Proposals: {run.proposal_source === "model_proposal" ? "model" : "deterministic templates"} — {run.model_status}
            {run.stop_reason && <> · Stopped: {run.stop_reason}</>}
          </div>

          {run.candidates.map((c) => (
            <details key={c.candidate_id} className="border border-slate-800 rounded-lg bg-[#070a12]/60">
              <summary className="flex flex-wrap items-center gap-2 px-3 py-2 cursor-pointer select-none">
                <span className={`text-[10px] uppercase font-semibold px-1.5 py-0.5 rounded border ${CANDIDATE_CLS[c.status] || "border-slate-700 text-slate-300"}`}>
                  {c.status.replace("_", " ")}
                </span>
                <span className="text-slate-200">{c.name}</span>
                <span className="text-slate-500 font-mono text-[10px]">R{c.round} · {c.target_category}</span>
              </summary>
              <div className="px-3 pb-3 space-y-2">
                <p className="text-slate-300 m-0">{c.hypothesis}</p>
                {c.status === "rejected" || c.status === "skipped" ? (
                  <p className="text-amber-300/90 m-0">{c.validation_notes.join(" ")}</p>
                ) : (
                  <>
                    <TraceTable calls={c.tool_sequence} events={c.result?.events} expected={c.expected_policy_decisions} />
                    {c.result && (
                      <p className="text-slate-400 m-0">
                        Expected {c.expected_policy_decisions.join(", ")} · observed{" "}
                        {c.result.events.map((e) => e.policy_decision).join(", ")}
                      </p>
                    )}
                    <CanaryNote event={c.result?.canary_event} />
                  </>
                )}
              </div>
            </details>
          ))}
        </div>
      )}
    </Card>
  );
}

export function AttackLab({ report, focusTest, onResult }) {
  const [runningId, setRunningId] = useState(null);
  const [error, setError] = useState(null);
  const testRefs = useRef({});
  const resultsMap = Object.fromEntries((report.results || []).map((r) => [r.test_id, r]));

  useEffect(() => {
    if (focusTest && testRefs.current[focusTest]) {
      testRefs.current[focusTest].scrollIntoView({ block: "start", behavior: "smooth" });
    }
  }, [focusTest]);

  const handleRunTest = async (testCase) => {
    setRunningId(testCase.test_id);
    setError(null);
    try {
      onResult(await api.runTest(report.scan_id, testCase.test_id));
    } catch (err) {
      setError(err.message);
    } finally {
      setRunningId(null);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <ErrorAlert message={error} onClose={() => setError(null)} />
      <p className="text-xs text-slate-500 m-0">
        All tool calls are simulated against mock tools; nothing in the skill is executed and no request leaves the harness.
      </p>

      {report.tests.map((test) => {
        const result = resultsMap[test.test_id];
        return (
          <div key={test.test_id} ref={(el) => { testRefs.current[test.test_id] = el; }}>
            <Card
              title={`${test.test_id} · ${test.name}`}
              subtitle={`${test.kind === "benign_control" ? "Benign control" : "Adversarial"} · ${
                test.origin === "model_proposed" ? "model-proposed (validated)" : "fixed suite"
              }`}
              icon={Terminal}
              className={focusTest === test.test_id ? "border-blue-500 ring-2 ring-blue-500/20" : ""}
              actions={
                <div className="flex items-center gap-2">
                  <StatusBadge status={result?.status} />
                  <button
                    type="button"
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-md text-xs disabled:opacity-50 cursor-pointer"
                    disabled={runningId === test.test_id}
                    onClick={() => handleRunTest(test)}
                  >
                    <Play size={11} /> {runningId === test.test_id ? "Running…" : "Run"}
                  </button>
                </div>
              }
            >
              <div className="space-y-2.5">
                <p className="text-xs text-slate-300 leading-relaxed m-0">{test.purpose}</p>
                <TraceTable calls={test.tool_sequence} events={result?.events} expected={test.expected_policy_decisions} />
                {result && <p className="text-xs text-slate-400 m-0">{result.summary}</p>}
                <CanaryNote event={result?.canary_event} />
              </div>
            </Card>
          </div>
        );
      })}

      {report.rejected_tests?.length > 0 && (
        <details className="bg-[#0e1424] border border-slate-800 rounded-xl p-4 text-xs">
          <summary className="cursor-pointer text-slate-400">
            {report.rejected_tests.length} model-proposed test(s) rejected by validation (not run)
          </summary>
          <ul className="list-disc pl-4 mt-2 space-y-1 text-slate-300">
            {report.rejected_tests.map((rt) => (
              <li key={rt.test_id}>
                <strong>{rt.name}</strong> — <span className="text-slate-400">{rt.validation_notes?.join("; ")}</span>
              </li>
            ))}
          </ul>
        </details>
      )}

      <AdaptivePanel key={report.scan_id} scanId={report.scan_id} />
    </div>
  );
}

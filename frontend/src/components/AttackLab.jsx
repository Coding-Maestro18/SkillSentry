import React, { useState, useRef, useEffect } from "react";
import {
  Play,
  Shield,
  Terminal,
  AlertTriangle,
  ShieldAlert,
  Flame,
  CheckCircle2,
  XCircle,
  Clock,
  RotateCw,
  StopCircle,
  Hash,
} from "lucide-react";
import { api } from "../api/client";
import { Card, DecisionBadge, StatusBadge } from "./CommonUI";

export function AttackLab({ report, focusTest, onResult }) {
  const [runningId, setRunningId] = useState(null);
  const [error, setError] = useState(null);
  const testRefs = useRef({});

  // Adaptive Red-Team State
  const [redTeamRun, setRedTeamRun] = useState(null);
  const [isStartingAdaptive, setIsStartingAdaptive] = useState(false);
  const [isAdvancingAdaptive, setIsAdvancingAdaptive] = useState(false);

  const resultsMap = Object.fromEntries(
    (report.results || []).map((r) => [r.test_id, r])
  );

  useEffect(() => {
    if (focusTest && testRefs.current[focusTest]) {
      testRefs.current[focusTest].scrollIntoView({ block: "start", behavior: "smooth" });
    }
  }, [focusTest]);

  const handleRunTest = async (testCase) => {
    setRunningId(testCase.test_id);
    setError(null);
    try {
      const res = await api.runTest(report.scan_id, testCase.test_id);
      onResult(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setRunningId(null);
    }
  };

  // Adaptive Red Team Actions
  const handleStartAdaptive = async () => {
    setIsStartingAdaptive(true);
    setError(null);
    try {
      const run = await api.startRedTeam(report.scan_id, true);
      setRedTeamRun(run);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsStartingAdaptive(false);
    }
  };

  const handleAdvanceAdaptive = async () => {
    if (!redTeamRun) return;
    setIsAdvancingAdaptive(true);
    setError(null);
    try {
      const run = await api.advanceRedTeamRound(redTeamRun.run_id);
      setRedTeamRun(run);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsAdvancingAdaptive(false);
    }
  };

  const handleStopAdaptive = async () => {
    if (!redTeamRun) return;
    try {
      const run = await api.stopRedTeamRun(redTeamRun.run_id);
      setRedTeamRun(run);
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      {error && (
        <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-300 text-xs flex items-center gap-2">
          <AlertTriangle size={15} />
          <span>{error}</span>
        </div>
      )}

      {/* Adaptive Red-Team Section */}
      <Card
        title="Adaptive Red-Team Workbench"
        subtitle="Bounded propose-validate-simulate loop exploring follow-up adversarial vectors"
        icon={Flame}
        actions={
          <div className="flex items-center gap-2">
            {!redTeamRun ? (
              <button
                type="button"
                onClick={handleStartAdaptive}
                disabled={isStartingAdaptive}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-rose-600 hover:bg-rose-500 text-white rounded-md text-xs font-semibold transition-colors cursor-pointer disabled:opacity-50"
              >
                <Flame size={13} />
                <span>{isStartingAdaptive ? "Launching Campaign..." : "Start Adaptive Red Team"}</span>
              </button>
            ) : (
              <div className="flex items-center gap-2">
                {redTeamRun.status === "running" && (
                  <button
                    type="button"
                    onClick={handleAdvanceAdaptive}
                    disabled={isAdvancingAdaptive || redTeamRun.current_round >= redTeamRun.max_rounds}
                    className="inline-flex items-center gap-1.5 px-3 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded-md text-xs font-medium transition-colors cursor-pointer disabled:opacity-50"
                  >
                    <RotateCw size={12} className={isAdvancingAdaptive ? "animate-spin" : ""} />
                    <span>{isAdvancingAdaptive ? "Advancing..." : `Advance Round (${redTeamRun.current_round + 1}/3)`}</span>
                  </button>
                )}
                {redTeamRun.status === "running" && (
                  <button
                    type="button"
                    onClick={handleStopAdaptive}
                    className="inline-flex items-center gap-1.5 px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-md text-xs font-medium transition-colors cursor-pointer"
                  >
                    <StopCircle size={12} />
                    <span>Stop</span>
                  </button>
                )}
                <span className={`text-[11px] px-2.5 py-0.5 rounded-full border font-semibold uppercase ${
                  redTeamRun.status === "completed"
                    ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                    : redTeamRun.status === "stopped"
                    ? "bg-amber-500/10 text-amber-400 border-amber-500/30"
                    : "bg-blue-500/10 text-blue-400 border-blue-500/30"
                }`}>
                  {redTeamRun.status}
                </span>
              </div>
            )}
          </div>
        }
      >
        {!redTeamRun ? (
          <p className="text-xs text-slate-400 m-0">
            Adaptive mode evaluates completed scan findings and initial test results to propose targeted follow-up scenarios.
            Hard budgets: max 3 rounds, max 3 candidates per round, max 9 tests executed total. Server-side validation rejects any code/shell execution.
          </p>
        ) : (
          <div className="space-y-4">
            {/* Metrics Bar */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 p-3 bg-[#070a12] border border-slate-800 rounded-lg text-xs">
              <div>
                <span className="text-slate-400 block text-[11px]">Round</span>
                <strong className="text-slate-200 font-mono text-sm">
                  {redTeamRun.current_round} / {redTeamRun.max_rounds}
                </strong>
              </div>
              <div>
                <span className="text-slate-400 block text-[11px]">Candidates Evaluated</span>
                <strong className="text-slate-200 font-mono text-sm">
                  {redTeamRun.candidates.length} (acc: {redTeamRun.metrics?.candidates_accepted || 0}, rej: {redTeamRun.metrics?.candidates_rejected || 0})
                </strong>
              </div>
              <div>
                <span className="text-slate-400 block text-[11px]">Tests Executed</span>
                <strong className="text-slate-200 font-mono text-sm">
                  {redTeamRun.metrics?.tests_executed || 0} / {redTeamRun.max_tests_total}
                </strong>
              </div>
              <div>
                <span className="text-slate-400 block text-[11px]">Benign Control</span>
                <strong className={redTeamRun.benign_control_passed ? "text-emerald-400 font-mono text-sm" : "text-rose-400 font-mono text-sm"}>
                  {redTeamRun.benign_control_passed ? "PASSED (Safe)" : "FLAGGED"}
                </strong>
              </div>
            </div>

            {/* Candidates Stream */}
            <div className="space-y-3">
              {redTeamRun.candidates.map((cand) => (
                <div
                  key={cand.candidate_id}
                  className="p-3 bg-[#0e1424] border border-slate-800 rounded-lg text-xs space-y-2"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[11px] text-slate-400 px-1.5 py-0.5 bg-slate-900 border border-slate-800 rounded">
                        {cand.candidate_id}
                      </span>
                      <strong className="text-slate-200 text-xs">{cand.name}</strong>
                      <span className="text-[10px] text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded-full">
                        {cand.target_category}
                      </span>
                    </div>

                    <span className={`text-[11px] px-2 py-0.5 rounded-full font-semibold ${
                      cand.status === "passed"
                        ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
                        : cand.status === "failed"
                        ? "bg-rose-500/15 text-rose-400 border border-rose-500/30"
                        : cand.status === "rejected"
                        ? "bg-amber-500/15 text-amber-400 border border-amber-500/30"
                        : "bg-slate-800 text-slate-300"
                    }`}>
                      {cand.status.toUpperCase()}
                    </span>
                  </div>

                  <p className="text-slate-300 text-xs m-0 leading-relaxed">
                    <strong>Hypothesis:</strong> {cand.hypothesis}
                  </p>

                  {cand.validation_notes?.length > 0 && (
                    <div className="text-[11px] text-slate-400 bg-[#070a12] p-2 rounded border border-slate-800/80">
                      <strong>Validation:</strong> {cand.validation_notes.join("; ")}
                    </div>
                  )}

                  {cand.result && (
                    <div className="space-y-1.5 pt-1 border-t border-slate-800">
                      <div className="text-[11px] text-slate-400">
                        Result: <strong className="text-slate-200">{cand.result.summary}</strong>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {cand.result.events?.map((ev, i) => (
                          <div key={i} className="inline-flex items-center gap-1.5 font-mono text-[10px] bg-slate-900 px-2 py-1 rounded border border-slate-800">
                            <span>{ev.tool_name}</span>
                            <DecisionBadge decision={ev.policy_decision} />
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </Card>

      {/* Baseline Test Cases List */}
      <div className="flex flex-col gap-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-2">
          <h3 className="text-sm font-bold text-slate-200 m-0">Baseline Fixed & Model Test Suite</h3>
          <span className="text-xs text-slate-400">{report.tests.length} Scenarios</span>
        </div>

        {report.tests.map((test) => {
          const result = resultsMap[test.test_id];
          const isFocused = focusTest === test.test_id;
          const canary = result?.canary_event;

          return (
            <div
              key={test.test_id}
              ref={(el) => { testRefs.current[test.test_id] = el; }}
            >
              <Card
                title={`${test.test_id} · ${test.name}`}
                subtitle={`Trigger: ${test.trigger?.type || "Rule"} ${test.trigger?.rule_ids?.join(", ") || ""}`}
                icon={Terminal}
                className={isFocused ? "border-blue-500 ring-2 ring-blue-500/20" : ""}
                actions={
                  <div className="flex items-center gap-2">
                    <StatusBadge status={result?.status} />
                    <button
                      type="button"
                      className="inline-flex items-center gap-1.5 px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-md text-xs font-medium transition-colors disabled:opacity-50 cursor-pointer"
                      disabled={runningId === test.test_id}
                      onClick={() => handleRunTest(test)}
                    >
                      <Play size={12} />
                      <span>{runningId === test.test_id ? "Simulating..." : "Run Again"}</span>
                    </button>
                  </div>
                }
              >
                <div className="space-y-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-[10px] text-slate-400 bg-slate-900 border border-slate-800 px-2 py-0.5 rounded">
                      Kind: {test.kind}
                    </span>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full border ${
                      test.origin === "model_proposed"
                        ? "bg-purple-500/10 text-purple-300 border-purple-500/30 font-semibold"
                        : "bg-slate-900 text-slate-400 border-slate-800 font-mono"
                    }`}>
                      Origin: {test.origin === "model_proposed" ? "Model-Generated (Validated)" : "Fixed Suite"}
                    </span>
                  </div>

                  <p className="text-xs text-slate-300 leading-relaxed m-0">
                    {test.purpose}
                  </p>

                  {/* Canary Observation Callout (Feature B) */}
                  {canary && (
                    <div className={`p-3 rounded-lg border text-xs space-y-1.5 ${
                      canary.status === "matched"
                        ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-200"
                        : canary.status === "blocked_before_send"
                        ? "bg-amber-500/10 border-amber-500/30 text-amber-200"
                        : "bg-slate-900/80 border-slate-800 text-slate-300"
                    }`}>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Hash size={14} className={canary.status === "matched" ? "text-emerald-400" : "text-amber-400"} />
                          <strong>Canary Token Detection:</strong>
                          <span className="font-mono text-[11px] uppercase px-2 py-0.5 rounded bg-slate-950 border border-slate-800">
                            {canary.status}
                          </span>
                        </div>
                        {canary.token_digest && (
                          <span className="font-mono text-[10px] text-slate-400">
                            Digest: {canary.token_digest}
                          </span>
                        )}
                      </div>
                      <p className="m-0 text-[11px] leading-relaxed">
                        {canary.notes}
                      </p>
                      <div className="text-[10px] text-slate-400 italic">
                        Synthetic canary; mock payload only; no real network request was sent.
                      </div>
                    </div>
                  )}

                  {/* Tool Sequence Table */}
                  <div className="overflow-x-auto border border-slate-800 rounded-lg">
                    <table className="w-full text-left border-collapse text-xs">
                      <thead>
                        <tr className="bg-[#0b101d] text-slate-400 border-b border-slate-800">
                          <th className="py-2 px-3 font-medium">#</th>
                          <th className="py-2 px-3 font-medium">Tool Call</th>
                          <th className="py-2 px-3 font-medium">Arguments</th>
                          <th className="py-2 px-3 font-medium">Policy Gate Decision</th>
                          <th className="py-2 px-3 font-medium">Mock Summary</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 bg-[#070a12]/50">
                        {test.tool_sequence.map((call, idx) => {
                          const event = result?.events?.[idx];
                          return (
                            <tr key={idx} className="hover:bg-slate-800/30 transition-colors">
                              <td className="py-2 px-3 text-slate-500 font-mono text-[11px]">{idx + 1}</td>
                              <td className="py-2 px-3 font-mono font-medium text-blue-400 text-[11px]">{call.tool}</td>
                              <td className="py-2 px-3 font-mono text-[11px] text-slate-300">
                                {Object.entries(call.args).map(([k, v]) => (
                                  <div key={k}>
                                    <span className="text-slate-500">{k}:</span> {v}
                                  </div>
                                ))}
                              </td>
                              <td className="py-2 px-3">
                                {event ? (
                                  <div className="flex flex-col gap-0.5">
                                    <DecisionBadge decision={event.policy_decision} />
                                    <span className="text-[10px] text-slate-500">{event.decision_reason}</span>
                                  </div>
                                ) : (
                                  <span className="text-slate-500 font-mono text-[11px]">Expected: {test.expected_policy_decisions[idx]}</span>
                                )}
                              </td>
                              <td className="py-2 px-3 text-slate-400 text-xs">
                                {event ? (
                                  <div className="text-slate-400 font-mono text-[11px]">
                                    {event.mock_result_summary}
                                  </div>
                                ) : (
                                  <span className="text-slate-500">—</span>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>

                  {result && (
                    <div className="flex items-center justify-between text-xs bg-[#070a12] border border-slate-800 p-2.5 rounded-lg">
                      <span className="text-slate-400">
                        Expected Outcome: <strong className="text-slate-200">{test.expected_outcome}</strong>
                      </span>
                      <span className="text-slate-200">
                        Result: <strong>{result.summary}</strong>
                      </span>
                    </div>
                  )}
                </div>
              </Card>
            </div>
          );
        })}
      </div>

      {/* Rejected Model-Proposed Tests Section */}
      {report.rejected_tests?.length > 0 && (
        <Card
          title={`Rejected Model-Proposed Tests (${report.rejected_tests.length})`}
          subtitle="Tests proposed by model that violated strict deterministic safety schemas"
          icon={ShieldAlert}
        >
          <ul className="list-disc pl-4.5 space-y-1.5 text-xs text-slate-300 m-0">
            {report.rejected_tests.map((rt) => (
              <li key={rt.test_id}>
                <strong>{rt.name}</strong> —{" "}
                <span className="text-slate-400">{rt.validation_notes?.join("; ")}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}

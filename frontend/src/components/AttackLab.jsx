import React, { useState, useRef, useEffect } from "react";
import { Play, Shield, Terminal, AlertTriangle, ShieldAlert } from "lucide-react";
import { api } from "../api/client";
import { Card, DecisionBadge, StatusBadge } from "./CommonUI";

export function AttackLab({ report, focusTest, onResult }) {
  const [runningId, setRunningId] = useState(null);
  const [error, setError] = useState(null);
  const testRefs = useRef({});

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

  return (
    <div className="flex flex-col gap-5">
      {/* Sandbox Notice Banner */}
      <div className="p-3.5 bg-blue-500/10 border border-blue-500/25 rounded-xl text-blue-200 text-xs flex items-center gap-3">
        <Shield size={18} className="shrink-0 text-blue-400" />
        <div>
          <strong>Deterministic Mock Tool Sandbox:</strong> The harness intercepts and records all tool calls in memory. No real shell processes, sockets, or host credentials are touched. Tests <strong>fail</strong> when a skill induces an action blocked or flagged by the policy gate. Suite v{report.suite_version}.
        </div>
      </div>

      {error && (
        <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-300 text-xs flex items-center gap-2">
          <AlertTriangle size={15} />
          <span>{error}</span>
        </div>
      )}

      {/* Test Cases List */}
      <div className="flex flex-col gap-4">
        {report.tests.map((test) => {
          const result = resultsMap[test.test_id];
          const isFocused = focusTest === test.test_id;

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

                  {test.trigger?.excerpt && (
                    <div className="flex items-center gap-2 text-xs text-slate-400">
                      <span>Trigger text in skill:</span>
                      <code className="text-blue-300 font-mono bg-[#070a12] px-2 py-0.5 rounded border border-slate-800">
                        {test.trigger.excerpt}
                      </code>
                    </div>
                  )}

                  {/* Tool Sequence Table */}
                  <div className="overflow-x-auto border border-slate-800/80 rounded-lg">
                    <table className="w-full border-collapse text-left text-xs">
                      <thead>
                        <tr className="bg-[#141c30] text-slate-400 font-semibold border-b border-slate-800">
                          <th className="p-2.5 w-8">#</th>
                          <th className="p-2.5">Simulated Tool Call Signature</th>
                          <th className="p-2.5 w-24">Expected</th>
                          <th className="p-2.5 w-24">Observed</th>
                          <th className="p-2.5">Policy Gate Reason & Mock Outcome</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/80">
                        {test.tool_sequence.map((call, idx) => {
                          const event = result?.events?.[idx];
                          const formattedArgs = Object.entries(call.args || {})
                            .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
                            .join(", ");

                          return (
                            <tr key={idx} className="hover:bg-slate-800/30">
                              <td className="p-2.5 text-slate-500 font-mono">{idx + 1}</td>
                              <td className="p-2.5 font-mono text-blue-300">
                                {call.tool}({formattedArgs})
                              </td>
                              <td className="p-2.5">
                                <DecisionBadge decision={test.expected_policy_decisions?.[idx]} />
                              </td>
                              <td className="p-2.5">
                                {event ? (
                                  <DecisionBadge decision={event.policy_decision} />
                                ) : (
                                  <span className="text-slate-500 text-[11px]">Not Triggered</span>
                                )}
                              </td>
                              <td className="p-2.5 text-xs">
                                {event ? (
                                  <div className="space-y-0.5">
                                    <div className="text-slate-200 font-medium">
                                      {event.decision_reason}
                                    </div>
                                    <div className="text-slate-400 font-mono text-[11px]">
                                      {event.mock_result_summary}
                                    </div>
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

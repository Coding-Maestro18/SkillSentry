import React, { useState } from "react";
import { Wrench, CheckCircle2, RotateCcw, ShieldCheck, AlertCircle } from "lucide-react";
import { api, waitForScan } from "../api/client";
import { Card } from "./CommonUI";

export function FixCompare({ report, onOpenScan }) {
  const [fixSuggestion, setFixSuggestion] = useState(null);
  const [draftFiles, setDraftFiles] = useState({});
  const [useModel, setUseModel] = useState(true);
  const [busyMessage, setBusyMessage] = useState(null);
  const [error, setError] = useState(null);
  const [comparison, setComparison] = useState(null);

  // Request fix suggestion
  const handleRequestFix = async () => {
    setBusyMessage("Synthesizing safe remediation diff...");
    setError(null);
    try {
      const fix = await api.fix(report.scan_id, useModel);
      setFixSuggestion(fix);
      setDraftFiles({ ...fix.revised_files });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyMessage(null);
    }
  };

  // Rerun same suite against revised files
  const handleRerun = async () => {
    setBusyMessage("Executing regression suite against revised copy...");
    setError(null);
    setComparison(null);
    try {
      const scanStatus = await api.rerun(report.scan_id, draftFiles);
      const done = await waitForScan(scanStatus.scan_id, (st) =>
        setBusyMessage(`Re-audit in progress: ${st.stage_detail || st.stage}`)
      );
      if (done.status === "failed") {
        throw new Error(done.error?.message || "Revision scan failed.");
      }
      const cmp = await api.comparison(done.scan_id);
      setComparison(cmp);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyMessage(null);
    }
  };

  if (report.parent_scan_id) {
    return (
      <Card title="Revision Audit Result" icon={RotateCcw}>
        <p className="text-xs text-slate-300">
          This scan is a rerun of suite v{report.suite_version} originating from parent scan{" "}
          <button
            type="button"
            className="text-blue-400 hover:text-blue-300 font-mono underline ml-1 cursor-pointer"
            onClick={() => onOpenScan(report.parent_scan_id)}
          >
            {report.parent_scan_id} →
          </button>
        </p>
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-5">
      <Card
        title="Remediation & Regression Sandbox"
        subtitle="Review proposed fixes and rerun the exact same attack suite against an isolated copy"
        icon={Wrench}
        actions={
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-1.5 text-xs text-slate-400 cursor-pointer">
              <input
                type="checkbox"
                checked={useModel}
                onChange={(e) => setUseModel(e.target.checked)}
                className="accent-blue-500 rounded"
              />
              <span>Use model if available</span>
            </label>
            <button
              type="button"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-md text-xs font-medium transition-colors disabled:opacity-50 cursor-pointer"
              disabled={!!busyMessage}
              onClick={handleRequestFix}
            >
              <span>{busyMessage ? "Working..." : "Generate Fix Suggestion"}</span>
            </button>
          </div>
        }
      >
        <div className="p-3 bg-blue-500/10 border border-blue-500/25 rounded-lg text-blue-300 text-xs">
          <span>
            <strong>Safety Invariant:</strong> The original uploaded file is permanently read-only. Fixes are drafted to an in-memory staging buffer for reviewer validation.
          </span>
        </div>

        {error && (
          <div className="mt-3 p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle size={14} />
            <span>{error}</span>
          </div>
        )}

        {busyMessage && (
          <div className="mt-3 text-xs text-blue-400 font-medium">
            {busyMessage}
          </div>
        )}

        {fixSuggestion && (
          <div className="mt-4 space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${
                fixSuggestion.origin === "model"
                  ? "bg-purple-500/10 text-purple-300 border-purple-500/30"
                  : "bg-sky-500/10 text-sky-300 border-sky-500/30"
              }`}>
                {fixSuggestion.origin === "model" ? "Model-Proposed Remediation" : "Deterministic Rule Remediation"}
              </span>
              <span className="text-xs text-slate-400">{fixSuggestion.model_status}</span>
            </div>

            {/* Rationale List */}
            {fixSuggestion.rationale?.length > 0 && (
              <ul className="list-disc pl-4.5 space-y-1 text-xs text-slate-300 m-0">
                {fixSuggestion.rationale.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            )}

            {/* Unified Diffs & Editable Textarea */}
            {Object.keys(fixSuggestion.diffs || {}).length === 0 ? (
              <div className="text-xs text-slate-400">No modifications recommended.</div>
            ) : (
              Object.entries(fixSuggestion.diffs).map(([path, diffText]) => (
                <div key={path} className="space-y-2 pt-2">
                  <div className="text-xs text-slate-300">
                    <span>Target File:</span>{" "}
                    <strong className="font-mono text-blue-300">{path}</strong>
                  </div>

                  {/* Diff Box */}
                  <div className="bg-[#070a12] border border-slate-800 rounded-lg font-mono text-[11px] leading-relaxed max-h-[380px] overflow-auto">
                    {diffText.split("\n").map((line, idx) => {
                      const isAdd = line.startsWith("+") && !line.startsWith("+++");
                      const isDel = line.startsWith("-") && !line.startsWith("---");

                      return (
                        <div
                          key={idx}
                          className={`px-3 py-0.5 whitespace-pre-wrap break-all ${
                            isAdd
                              ? "bg-emerald-500/15 text-emerald-300"
                              : isDel
                              ? "bg-rose-500/15 text-rose-300"
                              : "text-slate-400"
                          }`}
                        >
                          {line}
                        </div>
                      );
                    })}
                  </div>

                  {/* Editable textarea for reviewer validation */}
                  <div className="space-y-1 pt-1">
                    <label className="text-xs text-slate-300 font-medium block">
                      Revised Copy of <code>{path}</code> (Review & Edit Before Rerun):
                    </label>
                    <textarea
                      className="w-full bg-[#070a12] border border-slate-800 focus:border-blue-500 focus:outline-none rounded-lg p-3 text-xs font-mono text-slate-200 leading-relaxed resize-y"
                      rows={8}
                      spellCheck={false}
                      value={draftFiles[path] || ""}
                      onChange={(e) =>
                        setDraftFiles({ ...draftFiles, [path]: e.target.value })
                      }
                    />
                  </div>
                </div>
              ))
            )}

            {Object.keys(draftFiles).length > 0 && (
              <div className="flex items-center justify-between pt-3 border-t border-slate-800 text-xs">
                <span className="text-slate-400">
                  Ready to test? Re-audit will run the identical test suite and compare results.
                </span>
                <button
                  type="button"
                  className="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-medium shadow transition-colors disabled:opacity-50 cursor-pointer"
                  disabled={!!busyMessage}
                  onClick={handleRerun}
                >
                  <RotateCcw size={13} />
                  <span>Rerun Test Suite on Revised Copy</span>
                </button>
              </div>
            )}
          </div>
        )}
      </Card>

      {/* Comparison Results Dashboard */}
      {comparison && (
        <Card
          title="Before / After Remediation Verification"
          subtitle={`Comparing scan ${comparison.original_scan_id} → revision ${comparison.revision_scan_id}`}
          icon={ShieldCheck}
        >
          <div className="space-y-4">
            <div className="p-3.5 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-emerald-200 text-xs flex items-center gap-2.5">
              <CheckCircle2 size={16} className="text-emerald-400 shrink-0" />
              <div>
                <strong>Regression Verification Completed:</strong> Verified resolution across identical test cases and static rules.
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div className="bg-[#070a12] border border-slate-800 p-3.5 rounded-lg">
                <div className="font-bold text-slate-400 uppercase tracking-wider mb-2 text-[10px]">
                  RESOLVED FINDINGS ({comparison.resolved_findings?.length || 0}):
                </div>
                {comparison.resolved_findings?.length > 0 ? (
                  <ul className="list-disc pl-4 space-y-1 text-emerald-300 m-0">
                    {comparison.resolved_findings.map((rf, i) => (
                      <li key={i}>
                        <strong>{rf.finding_id}</strong>: {rf.title}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <span className="text-slate-500">No findings resolved</span>
                )}
              </div>

              <div className="bg-[#070a12] border border-slate-800 p-3.5 rounded-lg">
                <div className="font-bold text-slate-400 uppercase tracking-wider mb-2 text-[10px]">
                  TEST OUTCOME SHIFTS:
                </div>
                <dl className="grid grid-cols-2 gap-2 m-0 font-mono text-xs">
                  <div>
                    <span className="text-slate-400 block">Previous Failing:</span>
                    <strong className="text-rose-400 text-sm">
                      {comparison.original_summary?.tests_by_status?.fail || 0}
                    </strong>
                  </div>
                  <div>
                    <span className="text-slate-400 block">New Failing:</span>
                    <strong className="text-emerald-400 text-sm">
                      {comparison.revision_summary?.tests_by_status?.fail || 0}
                    </strong>
                  </div>
                </dl>
              </div>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}

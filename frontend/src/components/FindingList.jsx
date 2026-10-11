import React, { useState, useMemo } from "react";
import { Filter, Code, ExternalLink, ShieldCheck } from "lucide-react";
import { Card, SeverityBadge, EvidenceTag, CopyButton } from "./CommonUI";

export function FindingList({ report, onShowSource, onShowTest }) {
  const [filterSev, setFilterSev] = useState("all");
  const [filterCat, setFilterCat] = useState("all");
  const [filterFile, setFilterFile] = useState("all");
  const [filterEv, setFilterEv] = useState("all");
  const [selectedId, setSelectedId] = useState(report.findings[0]?.finding_id || null);

  const categories = useMemo(
    () => [...new Set(report.findings.map((f) => f.category))].sort(),
    [report.findings]
  );
  const files = useMemo(
    () => [...new Set(report.findings.map((f) => f.source_file))].sort(),
    [report.findings]
  );
  const evidenceTypes = useMemo(
    () => [...new Set(report.findings.map((f) => f.evidence_type))].sort(),
    [report.findings]
  );

  const filtered = useMemo(() => {
    return report.findings.filter((f) => {
      if (filterSev !== "all" && f.severity !== filterSev) return false;
      if (filterCat !== "all" && f.category !== filterCat) return false;
      if (filterFile !== "all" && f.source_file !== filterFile) return false;
      if (filterEv !== "all" && f.evidence_type !== filterEv) return false;
      return true;
    });
  }, [report.findings, filterSev, filterCat, filterFile, filterEv]);

  const current = useMemo(
    () => report.findings.find((f) => f.finding_id === selectedId) || filtered[0] || null,
    [report.findings, selectedId, filtered]
  );

  return (
    <div className="flex flex-col gap-4">
      {/* Filters Toolbar */}
      <div className="flex flex-wrap items-center gap-3 p-3 bg-[#0e1424] border border-slate-800 rounded-xl text-xs">
        <div className="flex items-center gap-1.5 text-slate-400 font-medium">
          <Filter size={13} />
          <span>Filters:</span>
        </div>

        <select
          className="bg-[#0b0f1a] border border-slate-800 focus:border-blue-500 focus:outline-none rounded-md px-2.5 py-1 text-slate-200 cursor-pointer"
          value={filterSev}
          onChange={(e) => setFilterSev(e.target.value)}
        >
          <option value="all">Severity: All</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
          <option value="informational">Informational</option>
        </select>

        <select
          className="bg-[#0b0f1a] border border-slate-800 focus:border-blue-500 focus:outline-none rounded-md px-2.5 py-1 text-slate-200 cursor-pointer"
          value={filterCat}
          onChange={(e) => setFilterCat(e.target.value)}
        >
          <option value="all">Category: All</option>
          {categories.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>

        <select
          className="bg-[#0b0f1a] border border-slate-800 focus:border-blue-500 focus:outline-none rounded-md px-2.5 py-1 text-slate-200 cursor-pointer"
          value={filterFile}
          onChange={(e) => setFilterFile(e.target.value)}
        >
          <option value="all">File: All</option>
          {files.map((fl) => (
            <option key={fl} value={fl}>{fl}</option>
          ))}
        </select>

        <select
          className="bg-[#0b0f1a] border border-slate-800 focus:border-blue-500 focus:outline-none rounded-md px-2.5 py-1 text-slate-200 cursor-pointer"
          value={filterEv}
          onChange={(e) => setFilterEv(e.target.value)}
        >
          <option value="all">Evidence: All</option>
          {evidenceTypes.map((ev) => (
            <option key={ev} value={ev}>{ev}</option>
          ))}
        </select>

        <div className="ml-auto text-slate-400">
          Showing <strong className="text-slate-200">{filtered.length}</strong> of {report.findings.length} findings
        </div>
      </div>

      {/* Split Triage View */}
      <div className="grid grid-cols-1 lg:grid-cols-[380px_1fr] gap-4 items-start">
        {/* Left: Master Finding List */}
        <div className="max-h-[740px] overflow-y-auto flex flex-col gap-2 pr-1">
          {filtered.length === 0 ? (
            <div className="bg-[#0e1424] border border-slate-800 rounded-xl p-8 text-center text-slate-400 text-xs">
              No findings matching the selected filters.
            </div>
          ) : (
            filtered.map((f) => {
              const isSelected = current?.finding_id === f.finding_id;
              return (
                <div
                  key={f.finding_id}
                  onClick={() => setSelectedId(f.finding_id)}
                  className={`p-3 rounded-lg border transition-all cursor-pointer ${
                    isSelected
                      ? "bg-[#141c30] border-blue-500/80 shadow-[0_0_12px_rgba(59,130,246,0.18)]"
                      : "bg-[#0e1424] border-slate-800/80 hover:border-slate-700"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-1.5">
                    <div className="flex items-center gap-1.5">
                      <SeverityBadge severity={f.severity} />
                      <span className="font-mono text-[10px] text-slate-400 bg-slate-900 border border-slate-800 px-1.5 py-0.5 rounded">
                        {f.rule_id}
                      </span>
                    </div>
                    <span className="text-[11px] font-mono text-slate-500">{f.finding_id}</span>
                  </div>

                  <div className={`text-xs leading-snug mb-1.5 ${isSelected ? "font-semibold text-slate-100" : "text-slate-300"}`}>
                    {f.title}
                  </div>

                  <div className="flex items-center justify-between text-[11px] text-slate-500">
                    <span className="font-mono">
                      {f.source_file}:{f.line_start}
                    </span>
                    <EvidenceTag type={f.evidence_type} />
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Right: Master Finding Inspector */}
        <div>
          {current ? (
            <Card
              title={`${current.finding_id} · ${current.title}`}
              subtitle={`Rule: ${current.rule_id} · Category: ${current.category}`}
              actions={
                current.line_start > 0 && (
                  <button
                    type="button"
                    className="inline-flex items-center gap-1.5 px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-md text-xs font-medium transition-colors cursor-pointer"
                    onClick={() => onShowSource(current.source_file, current.line_start)}
                  >
                    <ExternalLink size={12} />
                    <span>Inspect in Forensic Viewer</span>
                  </button>
                )
              }
            >
              <div className="space-y-4">
                {/* Status & Evidence Tags Row */}
                <div className="flex flex-wrap items-center gap-2">
                  <SeverityBadge severity={current.severity} />
                  <EvidenceTag type={current.evidence_type} />
                  <span className="font-mono text-xs text-slate-400 bg-slate-900 border border-slate-800 px-2 py-0.5 rounded">
                    Status: {current.status}
                  </span>
                  {current.model_confidence && (
                    <span className="font-mono text-xs text-slate-400 bg-slate-900 border border-slate-800 px-2 py-0.5 rounded">
                      Confidence: {current.model_confidence}
                    </span>
                  )}
                </div>

                {/* Location Bar */}
                <div className="flex items-center justify-between bg-[#070a12] border border-slate-800/80 px-3 py-2 rounded-lg text-xs">
                  <div className="flex items-center gap-2 text-slate-300">
                    <Code size={14} className="text-slate-500" />
                    <span>Location:</span>
                    <strong className="font-mono text-slate-100">
                      {current.source_file}:{current.line_start}:{current.column_start}
                      {current.line_end !== current.line_start && ` – ${current.line_end}:${current.column_end}`}
                    </strong>
                  </div>
                  <CopyButton
                    text={`${current.source_file}:${current.line_start}`}
                    label="Copy Ref"
                  />
                </div>

                {/* Escaped Evidence Excerpt */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
                    <span>Observed Evidence Excerpt (Escaped & Sanitized):</span>
                    <CopyButton text={current.evidence} />
                  </div>
                  <pre className="bg-[#070a12] border border-slate-800/80 rounded-lg p-3 font-mono text-xs text-slate-300 overflow-x-auto max-h-[140px] whitespace-pre-wrap break-all m-0">
                    {current.evidence || "—"}
                  </pre>
                </div>

                {/* Deterministic Fact vs Model Interpretation */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                  <div className="p-3 bg-emerald-500/5 border border-emerald-500/20 rounded-lg">
                    <div className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider mb-1">
                      OBSERVED DETERMINISTIC FACT
                    </div>
                    <div className="text-slate-300 leading-relaxed">
                      {current.observed_fact}
                    </div>
                  </div>

                  <div className="p-3 bg-purple-500/5 border border-purple-500/20 rounded-lg">
                    <div className="text-[10px] font-bold text-purple-400 uppercase tracking-wider mb-1">
                      SEMANTIC & SECURITY IMPLICATION
                    </div>
                    <div className="text-slate-300 leading-relaxed">
                      {current.interpretation}
                    </div>
                  </div>
                </div>

                {/* Decoded Payload (if applicable) */}
                {current.decoded_payload && (
                  <div className="p-3 bg-rose-500/5 border border-rose-500/25 rounded-lg text-xs">
                    <div className="text-[10px] font-bold text-rose-400 uppercase tracking-wider mb-1">
                      DECODED HIDDEN PAYLOAD ({current.decoder || "Decoder"}):
                    </div>
                    <pre className="bg-transparent border-0 p-0 font-mono text-xs text-rose-200 overflow-x-auto m-0">
                      {current.decoded_payload}
                    </pre>
                  </div>
                )}

                {/* Homoglyph Comparison Skeleton (if applicable) */}
                {current.extra?.skeleton && (
                  <div className="space-y-1 text-xs">
                    <span className="text-slate-400 font-medium">Unicode Homoglyph Confusable Skeleton:</span>
                    <div className="bg-[#070a12] border border-slate-800 p-2 rounded font-mono text-slate-200">
                      {String(current.extra.skeleton)}
                    </div>
                    <span className="text-[11px] text-slate-500">
                      Demonstrates visual identifier collision with standard ASCII symbols.
                    </span>
                  </div>
                )}

                {/* Remediation Advice */}
                {current.remediation && (
                  <div className="p-3.5 bg-[#141c30] border border-slate-700/80 rounded-lg text-xs space-y-1">
                    <div className="flex items-center gap-1.5 font-semibold text-slate-100">
                      <ShieldCheck size={14} className="text-emerald-400" />
                      <span>Recommended Remediation</span>
                    </div>
                    <div className="text-slate-300 leading-relaxed">
                      {current.remediation}
                    </div>
                  </div>
                )}

                {/* Related Simulated Tests */}
                {current.related_test_ids?.length > 0 && (
                  <div className="flex items-center gap-2 text-xs pt-1">
                    <span className="text-slate-400">Related Attack Lab Scenarios:</span>
                    {current.related_test_ids.map((tid) => (
                      <button
                        key={tid}
                        type="button"
                        className="text-blue-400 hover:text-blue-300 font-mono hover:underline cursor-pointer"
                        onClick={() => onShowTest(tid)}
                      >
                        {tid} →
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </Card>
          ) : (
            <Card>
              <div className="text-center text-slate-500 text-xs p-12">
                Select a finding on the left to inspect detailed telemetry, character offsets, and remediation steps.
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

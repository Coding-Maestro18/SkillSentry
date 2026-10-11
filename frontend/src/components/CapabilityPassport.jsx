import React from "react";
import { ShieldAlert, ShieldCheck, AlertTriangle, FileCode, Check, EyeOff, Server, Terminal, Info } from "lucide-react";
import { Card } from "./CommonUI";

export function CapabilityPassport({ report }) {
  const p = report.passport;
  const s = report.summary;
  const m = report.model;

  if (!p || !s) return null;

  const hasHigh = (s.findings_by_severity.high || 0) > 0;
  const hasMed = (s.findings_by_severity.medium || 0) > 0;
  const testsFailing = s.tests_by_status.fail || 0;

  return (
    <div className="flex flex-col gap-6">
      {/* Top Level Security Verdict Banner */}
      <div
        className={`p-4 sm:p-5 rounded-xl border flex items-start gap-4 ${
          hasHigh || testsFailing > 0
            ? "bg-rose-500/10 border-rose-500/30 text-rose-200"
            : hasMed
            ? "bg-amber-500/10 border-amber-500/30 text-amber-200"
            : "bg-emerald-500/10 border-emerald-500/30 text-emerald-200"
        }`}
      >
        {hasHigh || testsFailing > 0 ? (
          <ShieldAlert size={24} className="shrink-0 text-rose-400 mt-0.5" />
        ) : hasMed ? (
          <AlertTriangle size={24} className="shrink-0 text-amber-400 mt-0.5" />
        ) : (
          <ShieldCheck size={24} className="shrink-0 text-emerald-400 mt-0.5" />
        )}
        <div className="flex flex-col gap-1 flex-1">
          <div className="text-base font-bold tracking-tight text-slate-100">
            {s.headline}
          </div>
          <div className="text-xs sm:text-sm text-slate-300 leading-relaxed">
            {hasHigh
              ? "High-severity security risks or policy violations detected in instructions or hidden metadata. Review findings before execution."
              : testsFailing > 0
              ? "One or more attack scenarios triggered simulated tool calls blocked by the mock policy gate."
              : "No high-severity risks identified. Findings below represent triage signals and informational observations."}
          </div>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
        <div className="bg-[#0e1424] border border-slate-800 rounded-xl p-4">
          <div className={`text-2xl font-bold font-mono ${hasHigh ? "text-rose-400" : "text-slate-100"}`}>
            {report.findings.length}
          </div>
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mt-1">
            Total Findings
          </div>
          <div className="flex flex-wrap gap-1.5 mt-2.5">
            <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-500/15 text-rose-300 border border-rose-500/30">
              {s.findings_by_severity.high || 0} high
            </span>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-500/15 text-amber-300 border border-amber-500/30">
              {s.findings_by_severity.medium || 0} med
            </span>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-sky-500/15 text-sky-300 border border-sky-500/30">
              {s.findings_by_severity.low || 0} low
            </span>
          </div>
        </div>

        <div className="bg-[#0e1424] border border-slate-800 rounded-xl p-4">
          <div className={`text-2xl font-bold font-mono ${testsFailing > 0 ? "text-rose-400" : "text-emerald-400"}`}>
            {testsFailing} / {s.tests_total}
          </div>
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mt-1">
            Adversarial Tests Blocked
          </div>
          <div className="text-xs text-slate-400 mt-2.5">
            {s.tests_by_status.pass || 0} passed policy gate
          </div>
        </div>

        <div className="bg-[#0e1424] border border-slate-800 rounded-xl p-4">
          <div className="text-2xl font-bold font-mono text-slate-100">
            {s.files_scanned} / {s.files_scanned + s.files_skipped}
          </div>
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mt-1">
            Files Inspected
          </div>
          <div className="text-xs text-slate-400 mt-2.5">
            {s.files_skipped > 0 ? `${s.files_skipped} skipped non-text` : "100% coverage"}
          </div>
        </div>

        <div className="bg-[#0e1424] border border-slate-800 rounded-xl p-4">
          <div className="text-2xl font-bold font-mono text-slate-100">
            {report.timings_ms ? `${Math.round(Object.values(report.timings_ms).reduce((a, b) => a + b, 0))} ms` : "—"}
          </div>
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mt-1">
            Scan Duration
          </div>
          <div className="text-xs text-slate-400 mt-2.5">
            Deterministic passes & mock trace
          </div>
        </div>
      </div>

      {/* Main Capability Passport & Technical Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 items-start">
        {/* Left: Capability Passport Card */}
        <Card
          title="Skill Capability Passport"
          subtitle="Declared specifications vs inferred runtime actions"
          icon={FileCode}
        >
          <dl className="grid grid-cols-[160px_1fr] gap-x-4 gap-y-2.5 text-xs m-0">
            <dt className="text-slate-400 font-medium">Declared Name</dt>
            <dd className="text-slate-100 font-semibold m-0">
              {p.skill_name || <span className="text-slate-500">None in frontmatter</span>}
            </dd>

            <dt className="text-slate-400 font-medium">Declared Purpose</dt>
            <dd className="text-slate-200 m-0 leading-relaxed">
              {p.description || <span className="text-slate-500">No declared description found</span>}
            </dd>

            <dt className="text-slate-400 font-medium">Declared Tools</dt>
            <dd className="m-0">
              {p.declared_capabilities?.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {p.declared_capabilities.map((c, i) => (
                    <span key={i} className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono text-[11px]">
                      {c}
                    </span>
                  ))}
                </div>
              ) : (
                <span className="text-slate-500">None declared</span>
              )}
            </dd>

            <dt className="text-slate-400 font-medium">Inferred by Rules</dt>
            <dd className="m-0">
              {p.inferred_capabilities_rules?.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {p.inferred_capabilities_rules.map((c, i) => (
                    <span key={i} className="px-2 py-0.5 rounded bg-blue-900/40 text-blue-300 border border-blue-500/30 font-mono text-[11px]">
                      {c}
                    </span>
                  ))}
                </div>
              ) : (
                <span className="text-slate-500">None inferred</span>
              )}
            </dd>

            <dt className="text-slate-400 font-medium">Inferred by Model</dt>
            <dd className="m-0">
              {p.inferred_capabilities_model?.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {p.inferred_capabilities_model.map((c, i) => (
                    <span key={i} className="px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-300 border border-purple-500/30 text-[11px]">
                      {c}
                    </span>
                  ))}
                </div>
              ) : (
                <span className="text-slate-500">{m?.status === "ok" ? "None inferred" : "Model unavailable"}</span>
              )}
            </dd>

            <dt className="text-slate-400 font-medium">Observed in Simulation</dt>
            <dd className="m-0">
              {p.observed_simulated_actions?.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {p.observed_simulated_actions.map((c, i) => (
                    <span key={i} className="px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/30 font-mono text-[11px]">
                      {c}
                    </span>
                  ))}
                </div>
              ) : (
                <span className="text-slate-500">No actions simulated</span>
              )}
            </dd>

            <dt className="text-slate-400 font-medium">Sensitive Keys Mentioned</dt>
            <dd className="m-0">
              {p.sensitive_items_mentioned?.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {p.sensitive_items_mentioned.map((c, i) => (
                    <span key={i} className="px-2 py-0.5 rounded-full bg-rose-500/15 text-rose-300 border border-rose-500/30 font-mono text-[11px]">
                      {c}
                    </span>
                  ))}
                </div>
              ) : (
                <span className="text-slate-500">None identified</span>
              )}
            </dd>

            <dt className="text-slate-400 font-medium">Outbound Destinations</dt>
            <dd className="m-0">
              {p.destinations_mentioned?.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {p.destinations_mentioned.map((c, i) => (
                    <span key={i} className="px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30 font-mono text-[11px]">
                      {c}
                    </span>
                  ))}
                </div>
              ) : (
                <span className="text-slate-500">No external hosts mentioned</span>
              )}
            </dd>
          </dl>

        </Card>

        {/* Right Stack: Unresolved Concerns & Deception Telemetry */}
        <div className="flex flex-col gap-5">
          <Card
            title="Unresolved Security Concerns"
            subtitle="Prioritized items requiring reviewer attention"
            icon={ShieldAlert}
          >
            {p.unresolved_concerns?.length > 0 ? (
              <ul className="list-disc pl-4.5 space-y-2 text-xs text-rose-300 m-0">
                {p.unresolved_concerns.map((concern, idx) => (
                  <li key={idx}>{concern}</li>
                ))}
              </ul>
            ) : (
              <div className="flex items-center gap-1.5 text-xs text-emerald-400">
                <Check size={14} />
                <span>No high or medium concerns flagged for manual triage.</span>
              </div>
            )}
          </Card>

          <Card
            title="Invisible Deception Scanner Telemetry"
            subtitle="Detected stealth techniques in Markdown/Unicode"
            icon={EyeOff}
          >
            {s.hidden_content_counts && Object.keys(s.hidden_content_counts).length > 0 ? (
              <div className="grid grid-cols-2 gap-2 text-xs">
                {Object.entries(s.hidden_content_counts).map(([type, count]) => (
                  <div
                    key={type}
                    className={`flex items-center justify-between p-2.5 rounded-lg border ${
                      count > 0
                        ? "bg-rose-500/10 border-rose-500/30 text-rose-300"
                        : "bg-[#070a12] border-slate-800 text-slate-400"
                    }`}
                  >
                    <span className="capitalize">{type.replace(/_/g, " ")}</span>
                    <span className="font-bold font-mono">{count}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-xs text-slate-500">No hidden content anomalies identified.</div>
            )}
          </Card>

          <Card
            title="Package File Inventory"
            subtitle={`${report.files.length} discovered items`}
            icon={Server}
          >
            <div className="overflow-x-auto border border-slate-800 rounded-lg">
              <table className="w-full border-collapse text-left text-xs">
                <thead>
                  <tr className="bg-[#141c30] text-slate-400 font-semibold border-b border-slate-800">
                    <th className="p-2.5">File Path</th>
                    <th className="p-2.5">Status</th>
                    <th className="p-2.5">Role</th>
                    <th className="p-2.5">Encoding</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/80">
                  {report.files.map((f) => (
                    <tr key={f.file_id} className="hover:bg-slate-800/30">
                      <td className="p-2.5 font-mono text-slate-200">{f.relative_path}</td>
                      <td className="p-2.5">
                        {f.scanned ? (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/15 text-emerald-300">
                            Inspected
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-500/15 text-slate-400">
                            Skipped
                          </span>
                        )}
                      </td>
                      <td className="p-2.5 text-slate-400">{f.role}</td>
                      <td className="p-2.5 text-slate-400 font-mono text-[11px]">
                        {f.encoding ? `${f.encoding} (${f.line_ending || "LF"})` : "binary"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      </div>

      {/* Audit Provenance & Environment Specifications */}
      <Card
        title="Audit Provenance & Boundary Disclosure"
        subtitle="Reproducible environment metadata"
        icon={Terminal}
      >
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 text-xs">
          <dl className="grid grid-cols-[160px_1fr] gap-x-3 gap-y-2 font-mono m-0">
            <dt className="text-slate-400">Analyzer Engine</dt>
            <dd className="text-slate-200 m-0">v{report.analyzer_version} (Ruleset {report.ruleset_version})</dd>

            <dt className="text-slate-400">Unicode Specs</dt>
            <dd className="text-slate-200 m-0">{report.unicode_version} (UTS39 {report.confusables_version})</dd>

            <dt className="text-slate-400">Simulation Suite</dt>
            <dd className="text-slate-200 m-0">Attack Lab Suite v{report.suite_version}</dd>

            <dt className="text-slate-400">Model Adapter</dt>
            <dd className="text-slate-200 m-0">
              {m ? `${m.name} (${m.provider})` : "Offline — deterministic scanner only"}
            </dd>
          </dl>

          <div>
            <span className="font-semibold text-slate-300 block mb-1.5">Known Scanner Boundaries:</span>
            <ul className="list-disc pl-4 space-y-1 text-slate-400 text-xs m-0">
              {report.limitations?.map((lim, idx) => (
                <li key={idx}>{lim}</li>
              ))}
            </ul>
          </div>
        </div>
      </Card>
    </div>
  );
}

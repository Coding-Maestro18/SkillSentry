import React from "react";
import { ShieldAlert, ShieldCheck, AlertTriangle, FileCode } from "lucide-react";
import { Card } from "./CommonUI";

function Chips({ items, empty, cls = "bg-slate-800 text-slate-300 border-slate-700" }) {
  if (!items?.length) return <span className="text-slate-500">{empty}</span>;
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((c, i) => (
        <span key={i} className={`px-2 py-0.5 rounded border font-mono text-[11px] ${cls}`}>{c}</span>
      ))}
    </div>
  );
}

function Stat({ value, label, detail, tone = "text-slate-100" }) {
  return (
    <div className="bg-[#0e1424] border border-slate-800 rounded-xl p-4">
      <div className={`text-2xl font-bold font-mono ${tone}`}>{value}</div>
      <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mt-1">{label}</div>
      {detail && <div className="text-xs text-slate-500 mt-1.5">{detail}</div>}
    </div>
  );
}

export function CapabilityPassport({ report }) {
  const p = report.passport;
  const s = report.summary;
  const m = report.model;
  if (!p || !s) return null;

  const sev = s.findings_by_severity;
  const hasHigh = (sev.high || 0) > 0;
  const hasMed = (sev.medium || 0) > 0;
  const failing = s.tests_by_status.fail || 0;
  const review = s.tests_by_status.needs_review || 0;
  const hidden = Object.entries(s.hidden_content_counts || {}).filter(([, n]) => n > 0);
  const canary = report.extensions?.canary_summary;
  const canaryParts = canary ? Object.entries(canary).filter(([, n]) => n > 0) : [];

  const tone = hasHigh || failing ? "rose" : hasMed ? "amber" : "emerald";
  const Icon = tone === "rose" ? ShieldAlert : tone === "amber" ? AlertTriangle : ShieldCheck;
  const toneCls = {
    rose: "bg-rose-500/10 border-rose-500/30 text-rose-400",
    amber: "bg-amber-500/10 border-amber-500/30 text-amber-400",
    emerald: "bg-emerald-500/10 border-emerald-500/30 text-emerald-400",
  }[tone];

  return (
    <div className="flex flex-col gap-5">
      <div className={`p-4 rounded-xl border flex items-center gap-3 ${toneCls}`}>
        <Icon size={22} className="shrink-0" />
        <div className="text-sm font-semibold text-slate-100">{s.headline}</div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Stat
          value={report.findings.length}
          label="Findings"
          detail={`${sev.high || 0} high · ${sev.medium || 0} medium · ${sev.low || 0} low`}
          tone={hasHigh ? "text-rose-400" : "text-slate-100"}
        />
        <Stat
          value={`${failing} / ${s.tests_total}`}
          label="Tests failing"
          detail={`${s.tests_by_status.pass || 0} pass${review ? ` · ${review} need review` : ""}`}
          tone={failing ? "text-rose-400" : "text-emerald-400"}
        />
        <Stat
          value={`${s.files_scanned} / ${s.files_scanned + s.files_skipped}`}
          label="Files scanned"
          detail={s.files_skipped ? `${s.files_skipped} not scanned (non-text)` : "All files scanned"}
        />
        <Stat
          value={hidden.reduce((a, [, n]) => a + n, 0)}
          label="Hidden-content signals"
          detail={hidden.length ? hidden.map(([k, n]) => `${n} ${k.replace(/_/g, " ")}`).join(" · ") : "None detected"}
          tone={hidden.length ? "text-amber-400" : "text-slate-100"}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 items-start">
        <Card title="Capability passport" subtitle="Declared vs. inferred vs. observed in simulation" icon={FileCode}>
          <dl className="grid grid-cols-[150px_1fr] gap-x-4 gap-y-2.5 text-xs m-0">
            <dt className="text-slate-400">Declared purpose</dt>
            <dd className="text-slate-200 m-0 leading-relaxed">
              {p.description || <span className="text-slate-500">No description in frontmatter</span>}
            </dd>
            <dt className="text-slate-400">Declared tools</dt>
            <dd className="m-0"><Chips items={p.declared_capabilities} empty="None declared" /></dd>
            <dt className="text-slate-400">Inferred (rules)</dt>
            <dd className="m-0">
              <Chips items={p.inferred_capabilities_rules} empty="None" cls="bg-blue-900/30 text-blue-300 border-blue-500/30" />
            </dd>
            <dt className="text-slate-400">Inferred (model)</dt>
            <dd className="m-0">
              <Chips
                items={p.inferred_capabilities_model}
                empty={m?.status === "ok" ? "None" : "Model unavailable"}
                cls="bg-purple-500/10 text-purple-300 border-purple-500/30"
              />
            </dd>
            <dt className="text-slate-400">Observed (simulated)</dt>
            <dd className="m-0">
              <Chips items={p.observed_simulated_actions} empty="None" cls="bg-amber-500/10 text-amber-300 border-amber-500/30" />
            </dd>
            <dt className="text-slate-400">Sensitive items</dt>
            <dd className="m-0">
              <Chips items={p.sensitive_items_mentioned} empty="None mentioned" cls="bg-rose-500/10 text-rose-300 border-rose-500/30" />
            </dd>
            <dt className="text-slate-400">Destinations</dt>
            <dd className="m-0">
              <Chips items={p.destinations_mentioned} empty="None mentioned" cls="bg-amber-500/10 text-amber-300 border-amber-500/30" />
            </dd>
          </dl>
        </Card>

        <Card title="Needs review" icon={ShieldAlert}>
          {p.unresolved_concerns?.length ? (
            <ul className="list-disc pl-4 space-y-1.5 text-xs text-slate-300 m-0">
              {p.unresolved_concerns.map((c, i) => <li key={i}>{c}</li>)}
            </ul>
          ) : (
            <p className="text-xs text-slate-400 m-0">No high or medium concerns.</p>
          )}
          {canaryParts.length > 0 && (
            <p className="text-xs text-slate-400 mt-3 mb-0">
              Canary checks (synthetic, mock payloads only):{" "}
              {canaryParts.map(([k, n]) => `${n} ${k.replace(/_/g, " ")}`).join(" · ")}
            </p>
          )}
        </Card>
      </div>

      <details className="bg-[#0e1424] border border-slate-800 rounded-xl p-4 text-xs text-slate-300 group">
        <summary className="cursor-pointer text-slate-400 font-medium select-none">
          Files, versions and limitations
        </summary>
        <div className="mt-4 grid grid-cols-1 lg:grid-cols-2 gap-5">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="text-slate-500 border-b border-slate-800">
                <th className="py-1.5 font-medium">File</th>
                <th className="py-1.5 font-medium">Scanned</th>
                <th className="py-1.5 font-medium">Role</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/70">
              {report.files.map((f) => (
                <tr key={f.file_id}>
                  <td className="py-1.5 font-mono text-slate-200">{f.relative_path}</td>
                  <td className="py-1.5">{f.scanned ? "yes" : "no"}</td>
                  <td className="py-1.5 text-slate-400">{f.role}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="space-y-3">
            <dl className="grid grid-cols-[130px_1fr] gap-x-3 gap-y-1.5 font-mono m-0">
              <dt className="text-slate-500">Analyzer</dt>
              <dd className="m-0">{report.analyzer_version} (rules {report.ruleset_version})</dd>
              <dt className="text-slate-500">Unicode data</dt>
              <dd className="m-0">{report.unicode_version} · confusables {report.confusables_version}</dd>
              <dt className="text-slate-500">Test suite</dt>
              <dd className="m-0">{report.suite_version}</dd>
              <dt className="text-slate-500">Model</dt>
              <dd className="m-0">
                {m ? `${m.name} · ${m.license} · ${m.inference_mode} · ${m.status}` : "not used"}
              </dd>
            </dl>
            {report.limitations?.length > 0 && (
              <ul className="list-disc pl-4 space-y-1 text-slate-400 m-0">
                {report.limitations.map((l, i) => <li key={i}>{l}</li>)}
              </ul>
            )}
          </div>
        </div>
      </details>
    </div>
  );
}

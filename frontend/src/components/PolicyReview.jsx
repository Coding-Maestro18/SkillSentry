import React, { useState, useEffect, useCallback } from "react";
import { CheckCircle2, XCircle, Download, Play, RefreshCw, Save } from "lucide-react";
import { api } from "../api/client";
import { Card, DecisionBadge, ErrorAlert } from "./CommonUI";

const btn =
  "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed";
const btnGray = `${btn} bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700`;

const OUTCOME = {
  contained: "text-emerald-300",
  pass: "text-emerald-300",
  not_contained: "text-rose-300",
  needs_review: "text-amber-300",
};

export function PolicyReview({ scanId }) {
  const [data, setData] = useState(null); // PolicyResponse for the selected revision
  const [yamlText, setYamlText] = useState("");
  const [check, setCheck] = useState(null); // validation of unsaved edits
  const [testRun, setTestRun] = useState(null);
  const [busy, setBusy] = useState("load");
  const [error, setError] = useState(null);

  const show = (res) => {
    setData(res);
    setYamlText(res.yaml);
    setCheck(null);
    setTestRun(null);
  };

  const act = useCallback(async (label, fn) => {
    setBusy(label);
    setError(null);
    try {
      await fn();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(null);
    }
  }, []);

  useEffect(() => {
    act("load", async () => show(await api.getPolicy(scanId)));
  }, [scanId, act]);

  if (!data) {
    return busy ? (
      <div className="p-8 text-center text-slate-400 text-sm">Loading policy…</div>
    ) : (
      <ErrorAlert message={error || "Policy unavailable."} />
    );
  }

  const edited = yamlText !== data.yaml;
  const validation = check || data.validation;
  const policy = data.policy;

  return (
    <div className="flex flex-col gap-4">
      <ErrorAlert message={error} onClose={() => setError(null)} />

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="text-xs text-slate-400 flex items-center gap-2">
          <span className="font-semibold text-slate-200 text-sm">SKILL_POLICY.yaml</span>
          <select
            className="bg-[#0b0f1a] border border-slate-800 rounded-md px-2 py-1 text-slate-200 font-mono"
            value={data.revision}
            onChange={(e) => act("load", async () => show(await api.getPolicy(scanId, Number(e.target.value))))}
          >
            {data.revisions.map((r) => (
              <option key={r} value={r}>
                r{String(r).padStart(3, "0")}{r === data.revisions[data.revisions.length - 1] ? " (latest)" : ""}
              </option>
            ))}
          </select>
          <span>
            {policy.metadata?.generator_mode === "user_edited" ? "edited by reviewer" : "generated (deterministic)"}
          </span>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button type="button" className={btnGray} disabled={!!busy}
            onClick={() => act("gen", async () => show(await api.generatePolicy(scanId)))}>
            <RefreshCw size={12} /> Regenerate
          </button>
          {edited ? (
            <>
              <button type="button" className={btnGray} disabled={!!busy}
                onClick={() => act("check", async () => setCheck(await api.validatePolicy(scanId, yamlText)))}>
                <CheckCircle2 size={12} /> Validate edits
              </button>
              <button type="button" className={`${btn} bg-blue-600 hover:bg-blue-500 text-white`} disabled={!!busy}
                onClick={() => act("save", async () => show(await api.savePolicyRevision(scanId, yamlText)))}>
                <Save size={12} /> Save as new revision
              </button>
            </>
          ) : (
            <>
              <button type="button" className={`${btn} bg-blue-600 hover:bg-blue-500 text-white`} disabled={!!busy}
                onClick={() => act("test", async () => setTestRun(await api.testPolicy(scanId, data.revision)))}>
                <Play size={12} /> {busy === "test" ? "Testing…" : "Test in mock gate"}
              </button>
              <a className={`${btn} bg-emerald-600 hover:bg-emerald-500 text-white`} href={api.policyExportUrl(scanId, data.revision)} download>
                <Download size={12} /> Download
              </a>
            </>
          )}
        </div>
      </div>

      <div className={`p-3 rounded-lg border text-xs ${validation.valid ? "border-emerald-500/30 text-emerald-300" : "border-rose-500/30 text-rose-300"}`}>
        <div className="flex items-center gap-2 font-semibold">
          {validation.valid ? <CheckCircle2 size={14} /> : <XCircle size={14} />}
          {validation.valid ? "Valid" : "Invalid — fix before saving"}
          {edited && <span className="text-slate-400 font-normal">(unsaved edits{check ? "" : ", not yet validated"})</span>}
        </div>
        {validation.errors?.length > 0 && (
          <ul className="list-disc pl-5 mt-1.5 space-y-0.5 text-rose-200">
            {validation.errors.map((e, i) => (
              <li key={i}><code>{e.field}</code>: {e.message}</li>
            ))}
          </ul>
        )}
        {validation.warnings?.length > 0 && (
          <ul className="list-disc pl-5 mt-1.5 space-y-0.5 text-amber-300">
            {validation.warnings.map((w, i) => <li key={i}>{w}</li>)}
          </ul>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_380px] gap-4 items-start">
        <textarea
          value={yamlText}
          onChange={(e) => { setYamlText(e.target.value); setCheck(null); }}
          rows={20}
          className="w-full font-mono text-xs p-3 bg-[#070a12] border border-slate-800 rounded-lg text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500"
          spellCheck={false}
        />
        <Card title="Why these rules">
          <ul className="space-y-2.5 text-xs m-0 p-0 list-none">
            {data.rationale.map((r, i) => (
              <li key={i}>
                <code className="text-blue-300">{r.field}</code>
                {r.value && <span className="text-slate-400"> = {r.value}</span>}
                <div className="text-slate-300">{r.reason}</div>
                {r.finding_ids?.length > 0 && (
                  <div className="text-slate-500 font-mono text-[10px]">from {r.finding_ids.join(", ")}</div>
                )}
              </li>
            ))}
          </ul>
          <p className="text-[11px] text-slate-500 mt-3 mb-0">
            A proposal: enforced only by the SkillSentry mock gate or a runtime that loads it.
          </p>
        </Card>
      </div>

      {testRun && (
        <Card title={`Mock gate results · r${String(testRun.revision).padStart(3, "0")}`}>
          <div className="space-y-2.5">
            {testRun.results.map((tr) => (
              <div key={tr.test_id} className="text-xs">
                <div className="flex items-center gap-2">
                  <span className="text-slate-200 font-medium">{tr.test_id} · {tr.name}</span>
                  <span className={`text-[11px] ${OUTCOME[tr.outcome] || "text-slate-400"}`}>{tr.note}</span>
                </div>
                <div className="flex flex-wrap gap-1.5 mt-1">
                  {tr.events.map((ev) => (
                    <span key={ev.sequence} className="inline-flex items-center gap-1 font-mono text-[10px] bg-slate-900 px-1.5 py-0.5 rounded border border-slate-800" title={ev.reason}>
                      {ev.tool} <DecisionBadge decision={ev.decision} />
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

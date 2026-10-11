import React, { useState, useEffect } from "react";
import { Shield, CheckCircle2, AlertTriangle, XCircle, Download, Play, RefreshCw, Code2, AlertCircle } from "lucide-react";
import { api } from "../api/client";
import { Card, DecisionBadge } from "./CommonUI";

export function PolicyReview({ scanId }) {
  const [loading, setLoading] = useState(true);
  const [policyData, setPolicyData] = useState(null);
  const [yamlText, setYamlText] = useState("");
  const [validation, setValidation] = useState(null);
  const [testResults, setTestResults] = useState(null);
  const [isSimulating, setIsSimulating] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [error, setError] = useState(null);

  const fetchPolicy = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getPolicy(scanId);
      setPolicyData(res.policy);
      setYamlText(res.yaml);
      setValidation(res.validation);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPolicy();
  }, [scanId]);

  const handleValidate = async () => {
    setIsValidating(true);
    setError(null);
    try {
      const val = await api.validatePolicy(scanId, { yaml: yamlText });
      setValidation(val);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsValidating(false);
    }
  };

  const handleSimulate = async () => {
    setIsSimulating(true);
    setError(null);
    try {
      const res = await api.testPolicy(scanId, { yaml: yamlText });
      setTestResults(res.results);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSimulating(false);
    }
  };

  const handleRegenerate = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.generatePolicy(scanId);
      setPolicyData(res.policy);
      setYamlText(res.yaml);
      setValidation(res.validation);
      setTestResults(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8 text-center text-slate-400 text-sm flex items-center justify-center gap-2">
        <RefreshCw size={16} className="animate-spin text-blue-400" />
        <span>Generating least-privilege policy proposal...</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-5">
      {error && (
        <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-300 text-xs flex items-center gap-2">
          <AlertTriangle size={15} />
          <span>{error}</span>
        </div>
      )}

      {/* Policy Header & Actions */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-4 bg-[#0e1424] border border-slate-800 rounded-xl">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-600/15 border border-blue-500/30 rounded-lg text-blue-400">
            <Shield size={20} />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-100 m-0">
              {policyData?.name || "SKILL_POLICY.yaml"}
            </h3>
            <span className="font-mono text-xs text-slate-400">
              ID: {policyData?.policy_id} · Schema: v{policyData?.schema_version || "1.0"}
            </span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={handleRegenerate}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-md text-xs font-medium transition-colors cursor-pointer"
          >
            <RefreshCw size={13} />
            <span>Regenerate Baseline</span>
          </button>
          <button
            type="button"
            onClick={handleValidate}
            disabled={isValidating}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-md text-xs font-medium transition-colors cursor-pointer"
          >
            <CheckCircle2 size={13} />
            <span>{isValidating ? "Validating..." : "Validate Policy"}</span>
          </button>
          <button
            type="button"
            onClick={handleSimulate}
            disabled={isSimulating}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-md text-xs font-medium transition-colors cursor-pointer"
          >
            <Play size={13} />
            <span>{isSimulating ? "Testing..." : "Test in Mock Gate"}</span>
          </button>
          <a
            href={api.policyExportUrl(scanId)}
            download
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-md text-xs font-medium transition-colors cursor-pointer"
          >
            <Download size={13} />
            <span>Download YAML</span>
          </a>
        </div>
      </div>

      {/* Validation Status Panel */}
      {validation && (
        <div className={`p-4 rounded-xl border text-xs flex flex-col gap-2 ${
          validation.valid ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300" : "bg-rose-500/10 border-rose-500/30 text-rose-300"
        }`}>
          <div className="flex items-center gap-2 font-semibold text-sm">
            {validation.valid ? (
              <>
                <CheckCircle2 size={16} className="text-emerald-400" />
                <span>Policy Semantics: Validated & Schema-Conformant</span>
              </>
            ) : (
              <>
                <XCircle size={16} className="text-rose-400" />
                <span>Policy Validation Failed: Revisions Required</span>
              </>
            )}
            <span className="ml-auto font-mono text-[11px] px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-300">
              Mode: {validation.generator_mode}
            </span>
          </div>

          {validation.errors?.length > 0 && (
            <ul className="list-disc pl-4 space-y-1 text-rose-200 mt-1">
              {validation.errors.map((err, i) => (
                <li key={i}>
                  <strong>[{err.code}]</strong> <em>{err.field}</em>: {err.message}
                </li>
              ))}
            </ul>
          )}

          {validation.warnings?.length > 0 && (
            <div className="mt-1 text-amber-300 flex flex-col gap-1">
              <span className="font-semibold">Review Warnings:</span>
              <ul className="list-disc pl-4 space-y-1">
                {validation.warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Policy YAML Editor / Viewer */}
      <Card
        title="SKILL_POLICY.yaml Specification"
        subtitle="Least-privilege tool allowlists, domain boundaries, and relative path scopes"
        icon={Code2}
      >
        <div className="space-y-3">
          <textarea
            value={yamlText}
            onChange={(e) => setYamlText(e.target.value)}
            rows={14}
            className="w-full font-mono text-xs p-3.5 bg-[#070a12] border border-slate-800 rounded-lg text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500"
            spellCheck={false}
          />
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>You may edit and click <strong>Validate Policy</strong> or <strong>Test in Mock Gate</strong>.</span>
            <span className="font-mono text-[11px]">YAML 1.2 · UTF-8</span>
          </div>
        </div>
      </Card>

      {/* Mock Gate Test Results */}
      {testResults && (
        <Card
          title="Mock Gate Policy Enforcement Results"
          subtitle="Exercising active scan test scenarios against proposed policy rules"
          icon={Shield}
        >
          <div className="space-y-3">
            {testResults.map((tr) => (
              <div key={tr.test_id} className="p-3 bg-[#070a12] border border-slate-800 rounded-lg text-xs space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-200">{tr.test_id} · {tr.name}</span>
                  <span className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                    tr.all_allowed ? "bg-emerald-500/20 text-emerald-300" : "bg-amber-500/20 text-amber-300"
                  }`}>
                    {tr.all_allowed ? "ALL ACTIONS ALLOWED" : "INTERCEPTED BY POLICY"}
                  </span>
                </div>
                <div className="space-y-1.5 pl-2 border-l border-slate-800">
                  {tr.events?.map((ev, i) => (
                    <div key={i} className="flex items-center gap-2 font-mono text-[11px]">
                      <span className="text-slate-400">Step {ev.sequence}: {ev.tool}</span>
                      <DecisionBadge decision={ev.decision} />
                      <span className="text-slate-500 font-sans text-xs">({ev.reason})</span>
                    </div>
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

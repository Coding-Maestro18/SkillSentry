import React, { useState } from "react";
import { Download, Shield, AlertTriangle, Eye, Terminal, Wrench, ShieldCheck } from "lucide-react";
import { api } from "../api/client";
import { CapabilityPassport } from "../components/CapabilityPassport";
import { FindingList } from "../components/FindingList";
import { ForensicViewer } from "../components/ForensicViewer";
import { AttackLab } from "../components/AttackLab";
import { FixCompare } from "../components/FixCompare";
import { PolicyReview } from "../components/PolicyReview";

const TABS = [
  { id: "overview", label: "Overview", icon: Shield },
  { id: "findings", label: "Findings", icon: AlertTriangle },
  { id: "forensic", label: "Source", icon: Eye },
  { id: "lab", label: "Attack Lab", icon: Terminal },
  { id: "policy", label: "Policy", icon: ShieldCheck },
  { id: "fix", label: "Fix & Retest", icon: Wrench },
];

export function ReportPage({ report, onUpdate, onOpenScan }) {
  const [activeTab, setActiveTab] = useState("overview");
  const [sourceTarget, setSourceTarget] = useState(null);
  const [focusTestId, setFocusTestId] = useState(null);

  const handleTestResultUpdate = (newResult) => {
    onUpdate({
      ...report,
      results: (report.results || []).map((r) =>
        r.test_id === newResult.test_id ? newResult : r
      ),
    });
  };

  const handleJumpToSource = (path, line) => {
    setSourceTarget({ path, line });
    setActiveTab("forensic");
  };

  const handleJumpToTest = (testId) => {
    setFocusTestId(testId);
    setActiveTab("lab");
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Report Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 sm:p-5 bg-[#0e1424] border border-slate-800 rounded-xl shadow-sm">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2.5">
            <h2 className="text-lg sm:text-xl font-bold text-slate-100 tracking-tight m-0">
              {report.skill_name || "Unnamed skill"}
            </h2>
            <span className="font-mono text-xs text-slate-400 bg-slate-900 border border-slate-800 px-2 py-0.5 rounded">
              {report.scan_id}
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400">
            <span>{new Date(report.created_at).toLocaleString()}</span>
            {report.parent_scan_id && (
              <span>
                · Revision of:{" "}
                <button
                  type="button"
                  className="text-blue-400 hover:text-blue-300 font-mono underline cursor-pointer"
                  onClick={() => onOpenScan(report.parent_scan_id)}
                >
                  {report.parent_scan_id} →
                </button>
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-1 text-xs text-slate-400">
          <Download size={13} className="mr-1" />
          {[["json", "JSON"], ["markdown", "Markdown"], ["sarif", "SARIF 2.1.0"]].map(([fmt, label]) => (
            <a
              key={fmt}
              className="px-2.5 py-1 rounded-md bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200"
              href={api.exportUrl(report.scan_id, fmt)}
              download
              title={fmt === "sarif" ? "SARIF file for code-scanning tools (download only; nothing is uploaded)" : undefined}
            >
              {label}
            </a>
          ))}
        </div>
      </div>

      {/* Primary Tab Navigation */}
      <nav className="flex items-center gap-1 border-b border-slate-800 overflow-x-auto pb-0 mb-2" role="tablist">
        {TABS.map((t) => {
          const Icon = t.icon;
          const isActive = activeTab === t.id;
          return (
            <button
              key={t.id}
              role="tab"
              aria-selected={isActive}
              className={`flex items-center gap-2 px-3.5 py-2.5 text-xs font-medium border-b-2 transition-colors whitespace-nowrap cursor-pointer ${
                isActive
                  ? "border-blue-500 text-slate-100 font-semibold"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
              onClick={() => setActiveTab(t.id)}
            >
              <Icon size={14} />
              <span>{t.label}</span>
              {t.id === "findings" && (
                <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-slate-800 text-slate-300">
                  {report.findings?.length || 0}
                </span>
              )}
              {t.id === "lab" && (
                <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-slate-800 text-slate-300">
                  {report.tests?.length || 0}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Tab Panels */}
      <div>
        {activeTab === "overview" && <CapabilityPassport report={report} />}

        {activeTab === "findings" && (
          <FindingList
            report={report}
            onShowSource={handleJumpToSource}
            onShowTest={handleJumpToTest}
          />
        )}

        {activeTab === "forensic" && (
          <ForensicViewer report={report} target={sourceTarget} />
        )}

        {activeTab === "lab" && (
          <AttackLab
            report={report}
            focusTest={focusTestId}
            onResult={handleTestResultUpdate}
          />
        )}

        {activeTab === "policy" && (
          <PolicyReview scanId={report.scan_id} />
        )}

        {activeTab === "fix" && (
          <FixCompare report={report} onOpenScan={onOpenScan} />
        )}
      </div>
    </div>
  );
}

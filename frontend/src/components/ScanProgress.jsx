import React from "react";
import { Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import { Card } from "./CommonUI";

const STAGES = [
  { id: "validating", label: "Validate archive" },
  { id: "parsing", label: "Parse files" },
  { id: "analyzing", label: "Static & hidden-content scan" },
  { id: "generating_tests", label: "Model review & test generation" },
  { id: "simulating", label: "Simulate tests in mock harness" },
  { id: "reporting", label: "Build report" },
];

export function ScanProgress({ status }) {
  if (!status) return null;

  const currentStageIndex = STAGES.findIndex((s) => s.id === status.status);
  const isFailed = status.status === "failed";

  return (
    <div className="max-w-[720px] mx-auto my-8">
      <Card
        title="Scanning…"
        subtitle={status.scan_id}
      >
        {isFailed ? (
          <div className="p-3.5 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle size={16} className="shrink-0" />
            <div>
              <strong>Scan Failed:</strong> {status.error?.message || "An unexpected error occurred during analysis."}
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center gap-2.5 text-blue-400 font-semibold text-sm">
              <Loader2 size={18} className="animate-spin text-blue-400" />
              <span>{status.stage_detail || "Analyzing package content..."}</span>
            </div>

            <div className="space-y-1.5 pt-2">
              {STAGES.map((s, idx) => {
                const isPast = currentStageIndex > idx || status.status === "completed";
                const isCurrent = status.status === s.id;

                return (
                  <div
                    key={s.id}
                    className={`flex items-center gap-3 px-3 py-2 rounded-lg text-xs transition-colors ${
                      isCurrent
                        ? "bg-[#141c30] border border-blue-500/40 text-slate-100 font-semibold"
                        : isPast
                        ? "text-slate-300"
                        : "text-slate-500 opacity-60"
                    }`}
                  >
                    {isPast ? (
                      <CheckCircle2 size={16} className="text-emerald-400 shrink-0" />
                    ) : isCurrent ? (
                      <Loader2 size={16} className="text-blue-400 animate-spin shrink-0" />
                    ) : (
                      <div className="w-4 h-4 rounded-full border border-slate-700 shrink-0" />
                    )}
                    <span>{s.label}</span>
                  </div>
                );
              })}
            </div>

          </div>
        )}
      </Card>
    </div>
  );
}

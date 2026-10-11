import React from "react";
import { Shield, RotateCcw, Cpu } from "lucide-react";

export function Header({ health, healthError, onReset, hasActiveReport }) {
  const model = health?.model;
  const isModelOnline = model?.status === "ok";

  return (
    <header className="sticky top-0 z-50 bg-[#090d16]/85 backdrop-blur-md border-b border-slate-800/80 px-5 py-5">
      <div className="max-w-[1440px] mx-auto flex items-center justify-between gap-4">
        {/* Brand */}
        <div className="flex items-center gap-2.5">
          <button
            type="button"
            className="flex items-center gap-2.5 text-2xl text-slate-100 font-bold tracking-tight bg-transparent border-none p-0 cursor-pointer hover:opacity-90 transition-opacity"
            onClick={onReset}
            title="SkillSentry Home"
          >
            {/* <div className="w-6.5 h-6.5 bg-gradient-to-br from-blue-500 to-blue-700 rounded flex items-center justify-center text-white shadow-[0_0_12px_rgba(59,130,246,0.35)]">
              <Shield size={15} />
            </div> */}
            <span>SkillSentry</span>
          </button>
        </div>

        {/* Action badges & controls */}
        <div className="flex items-center gap-3">
          {/* API Health pulse */}
          <div
            className="inline-flex items-center gap-1.5 text-xs text-slate-400 px-2.5 py-1 bg-[#0e1424] border border-slate-800 rounded-full"
            title={healthError || "API server reachable on port 8000"}
          >
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                healthError ? "bg-amber-400 shadow-[0_0_6px_#f59e0b]" : "bg-emerald-400 shadow-[0_0_6px_#10b981]"
              }`}
            />
            <span className="font-mono text-[11px]">API v{health?.analyzer_version || "0.1.0"}</span>
          </div>

          {/* Model Status Badge */}
          {model && (
            <div
              className="inline-flex items-center gap-1.5 text-xs text-slate-400 px-2.5 py-1 bg-[#0e1424] border border-slate-800 rounded-full font-mono text-[11px]"
              title={`${model.provider}: ${model.name || "None"} (${model.status_detail || model.status})`}
            >
              <Cpu size={12} className={isModelOnline ? "text-blue-400" : "text-slate-500"} />
              <span>
                {isModelOnline
                  ? model.name || "Model Online"
                  : `Static Mode (${model.provider})`}
              </span>
            </div>
          )}


          {/* Reset button */}
          {hasActiveReport && (
            <button
              type="button"
              className="inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-md transition-colors cursor-pointer"
              onClick={onReset}
            >
              <RotateCcw size={12} />
              <span>New Scan</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
}

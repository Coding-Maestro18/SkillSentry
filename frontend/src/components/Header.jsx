import React from "react";
import { RotateCcw, Network } from "lucide-react";

export function Header({ health, healthError, onReset, hasActiveReport, isCampaignMode, onToggleCampaigns }) {
  const model = health?.model;
  const modelOk = model?.status === "ok";
  const statusText = healthError
    ? "API offline"
    : !model
    ? "Connecting…"
    : modelOk
    ? model.name
    : "Static analysis only";

  return (
    <header className="sticky top-0 z-50 bg-[#090d16]/90 backdrop-blur-md border-b border-slate-800/80 px-5 py-3.5">
      <div className="max-w-[1440px] mx-auto flex items-center justify-between gap-4">
        <button
          type="button"
          className="text-xl text-slate-100 font-bold tracking-tight bg-transparent border-none p-0 cursor-pointer hover:opacity-90"
          onClick={onReset}
        >
          SkillSentry
        </button>

        <div className="flex items-center gap-3">
          <span
            className="hidden sm:inline-flex items-center gap-1.5 text-xs text-slate-400"
            title={healthError || (model ? `${model.provider}: ${model.status_detail || model.status}` : "")}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${healthError ? "bg-rose-400" : modelOk ? "bg-emerald-400" : "bg-amber-400"}`} />
            {statusText}
          </span>

          <button
            type="button"
            className={`inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-md cursor-pointer border transition-colors ${
              isCampaignMode
                ? "bg-blue-600 text-white border-blue-500"
                : "bg-slate-800 hover:bg-slate-700 text-slate-200 border-slate-700"
            }`}
            onClick={onToggleCampaigns}
          >
            <Network size={12} />
            Campaigns
          </button>

          {(hasActiveReport || isCampaignMode) && (
            <button
              type="button"
              className="inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-md cursor-pointer"
              onClick={onReset}
            >
              <RotateCcw size={12} />
              New scan
            </button>
          )}
        </div>
      </div>
    </header>
  );
}

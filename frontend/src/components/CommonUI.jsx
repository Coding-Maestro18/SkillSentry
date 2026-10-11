import React, { useState } from "react";
import { Check, Copy, AlertTriangle, AlertCircle, Info, ShieldCheck } from "lucide-react";

export function Card({ title, subtitle, icon: Icon, actions, children, className = "", titleClassName = "" }) {
  return (
    <div className={`bg-[#0e1424] border border-slate-800 rounded-xl p-5 hover:border-slate-700/80 transition-colors shadow-sm ${className}`}>
      {(title || actions) && (
        <div className="flex items-center justify-between gap-3 mb-3.5">
          <div className="flex flex-col gap-0.5">
            <h3 className={`font-semibold text-slate-100 flex items-center gap-2 m-0 ${titleClassName || "text-sm"}`}>
              {Icon && <Icon size={16} className="text-slate-400" />}
              {title}
            </h3>
            {subtitle && <span className="text-xs text-slate-400">{subtitle}</span>}
          </div>
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </div>
      )}
      {children}
    </div>
  );
}

export function SeverityBadge({ severity }) {
  const map = {
    high: {
      label: "High",
      cls: "bg-rose-500/15 text-rose-300 border-rose-500/35",
      icon: AlertCircle,
    },
    medium: {
      label: "Medium",
      cls: "bg-amber-500/15 text-amber-300 border-amber-500/35",
      icon: AlertTriangle,
    },
    low: {
      label: "Low",
      cls: "bg-sky-500/15 text-sky-300 border-sky-500/35",
      icon: Info,
    },
    informational: {
      label: "Info",
      cls: "bg-slate-500/15 text-slate-300 border-slate-500/35",
      icon: Info,
    },
  };
  const conf = map[severity] || map.informational;
  const Icon = conf.icon;
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-semibold uppercase tracking-wider border leading-tight ${conf.cls}`}
    >
      <Icon size={11} />
      {conf.label}
    </span>
  );
}

export function DecisionBadge({ decision }) {
  if (decision === "ALLOW") {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/35 uppercase">
        ALLOW
      </span>
    );
  }
  if (decision === "BLOCK") {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold bg-rose-500/15 text-rose-300 border border-rose-500/35 uppercase">
        BLOCK
      </span>
    );
  }
  if (decision === "FLAG") {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold bg-amber-500/15 text-amber-300 border border-amber-500/35 uppercase">
        FLAG
      </span>
    );
  }
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold bg-slate-500/15 text-slate-300 border border-slate-500/35">
      {decision || "—"}
    </span>
  );
}

export function StatusBadge({ status }) {
  if (status === "pass") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/35 uppercase">
        <ShieldCheck size={11} /> Pass
      </span>
    );
  }
  if (status === "fail") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-rose-500/15 text-rose-300 border border-rose-500/35 uppercase">
        <AlertCircle size={11} /> Fail
      </span>
    );
  }
  if (status === "needs_review") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-amber-500/15 text-amber-300 border border-amber-500/35 uppercase">
        <AlertTriangle size={11} /> Review
      </span>
    );
  }
  if (status === "skipped" || status === "not_run") {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold bg-slate-500/15 text-slate-300 border border-slate-500/35 uppercase">
        Skipped
      </span>
    );
  }
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold bg-slate-500/15 text-slate-300 border border-slate-500/35">
      {status || "Pending"}
    </span>
  );
}

export function EvidenceTag({ type }) {
  const map = {
    observed: {
      label: "Observed Fact",
      cls: "text-emerald-400 bg-emerald-500/10 border-emerald-500/25",
    },
    rule_based: {
      label: "Deterministic Rule",
      cls: "text-sky-400 bg-sky-500/10 border-sky-500/25",
    },
    model_interpretation: {
      label: "Model Hypothesis",
      cls: "text-purple-400 bg-purple-500/10 border-purple-500/25",
    },
    simulated: {
      label: "Harness Simulated",
      cls: "text-amber-400 bg-amber-500/10 border-amber-500/25",
    },
  };
  const conf = map[type] || { label: type, cls: "text-slate-400 bg-slate-500/10 border-slate-500/25" };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold border ${conf.cls}`}>
      {conf.label}
    </span>
  );
}

export function CopyButton({ text, label = "Copy" }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = (e) => {
    e.stopPropagation();
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      type="button"
      className="inline-flex items-center gap-1.5 px-2 py-1 text-xs text-slate-400 hover:text-slate-100 hover:bg-slate-800 rounded transition-colors cursor-pointer"
      onClick={handleCopy}
      title="Copy to clipboard"
    >
      {copied ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
      <span>{copied ? "Copied" : label}</span>
    </button>
  );
}

export function ErrorAlert({ message, onClose }) {
  if (!message) return null;
  return (
    <div className="p-3.5 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-300 text-xs flex items-center justify-between gap-3 mb-4">
      <div className="flex items-center gap-2">
        <AlertCircle size={16} className="text-rose-400 shrink-0" />
        <span>{message}</span>
      </div>
      {onClose && (
        <button
          type="button"
          className="text-rose-400 hover:text-rose-200 text-xs px-2 py-0.5 rounded hover:bg-rose-500/20 cursor-pointer"
          onClick={onClose}
        >
          Dismiss
        </button>
      )}
    </div>
  );
}

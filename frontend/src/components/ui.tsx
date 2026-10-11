import type { ReactNode } from "react";
import type { Decision, Severity } from "../types";

// Every status pairs colour with a glyph and a word, so meaning never relies on colour alone.
const SEV_GLYPH: Record<Severity, string> = { high: "▲", medium: "◆", low: "●", informational: "ⓘ" };

export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <span className={`badge sev-${severity}`} title={`Severity: ${severity} (a prioritization estimate, not proof of intent)`}>
      <span aria-hidden="true">{SEV_GLYPH[severity]}</span> {severity}
    </span>
  );
}

const DEC_GLYPH: Record<Decision, string> = { ALLOW: "✓", BLOCK: "⛔", FLAG: "⚑" };

export function DecisionBadge({ decision }: { decision: Decision }) {
  return (
    <span className={`badge dec-${decision.toLowerCase()}`}>
      <span aria-hidden="true">{DEC_GLYPH[decision]}</span> {decision}
    </span>
  );
}

const STATUS_GLYPH: Record<string, string> = { pass: "✓", fail: "✗", needs_review: "?", skipped: "–" };

export function StatusBadge({ status }: { status: string | null }) {
  const s = status ?? "not run";
  return (
    <span className={`badge st-${s.replace(/\s/g, "_")}`}>
      <span aria-hidden="true">{STATUS_GLYPH[s] ?? "·"}</span> {s.replace("_", " ")}
    </span>
  );
}

const EVIDENCE_LABEL: Record<string, string> = {
  observed: "Observed",
  rule_based: "Rule-based finding",
  model_interpretation: "Model interpretation",
  simulated: "Simulated behavior",
  user_confirmed: "User-confirmed",
};

export function EvidenceTag({ type }: { type: string }) {
  return <span className={`tag ev-${type}`}>{EVIDENCE_LABEL[type] ?? type}</span>;
}

export function Card({ title, children, actions }: { title?: ReactNode; children: ReactNode; actions?: ReactNode }) {
  return (
    <section className="card">
      {(title || actions) && (
        <header className="card-head">
          {title && <h3>{title}</h3>}
          {actions && <div className="card-actions">{actions}</div>}
        </header>
      )}
      {children}
    </section>
  );
}

export function List({ items, empty = "None" }: { items: string[]; empty?: string }) {
  if (!items.length) return <p className="muted">{empty}</p>;
  return (
    <ul className="plain-list">
      {items.map((x, i) => (
        <li key={i}>{x}</li>
      ))}
    </ul>
  );
}

export function ErrorBox({ error }: { error: string | null }) {
  if (!error) return null;
  return (
    <div className="error" role="alert">
      <strong>Error:</strong> {error}
    </div>
  );
}

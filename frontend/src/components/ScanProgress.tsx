import type { ScanStatus } from "../types";
import { Card } from "./ui";

const STEPS: { state: string; label: string }[] = [
  { state: "validating", label: "Validate files" },
  { state: "parsing", label: "Parse" },
  { state: "analyzing", label: "Static, hidden-content & model analysis" },
  { state: "generating_tests", label: "Generate tests" },
  { state: "simulating", label: "Simulate with mock tools" },
  { state: "reporting", label: "Create report" },
  { state: "completed", label: "Done" },
];

export default function ScanProgress({ status }: { status: ScanStatus }) {
  const idx = STEPS.findIndex((s) => s.state === status.status);
  return (
    <Card title={`Scanning ${status.scan_id}`}>
      <ol className="steps" aria-live="polite">
        {STEPS.map((s, i) => {
          const state = status.status === "failed" ? (i <= idx ? "done" : "todo") : i < idx ? "done" : i === idx ? "current" : "todo";
          return (
            <li key={s.state} className={`step ${state}`}>
              <span aria-hidden="true">{state === "done" ? "✓" : state === "current" ? "▶" : "○"}</span> {s.label}
            </li>
          );
        })}
      </ol>
      <p className="muted">{status.stage_detail}</p>
      {status.error && <p className="error">{status.error.message}</p>}
    </Card>
  );
}

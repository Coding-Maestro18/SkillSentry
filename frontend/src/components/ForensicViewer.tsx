import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api/client";
import type { FileView, ScanReport } from "../types";
import { Card, ErrorBox, SeverityBadge } from "./ui";

type Mode = "reveal" | "raw" | "preview";

const TYPE_GROUPS: Record<string, string[]> = {
  invisible: ["invisible_char", "bidi_control", "tag_char"],
  confusable: ["confusable"],
  comments: ["html_comment", "hidden_html"],
  whitespace: ["whitespace_anomaly", "unusual_space"],
};

interface Props {
  report: ScanReport;
  target: { path: string; line: number } | null;
}

export default function ForensicViewer({ report, target }: Props) {
  const scanned = report.files.filter((f) => f.scanned);
  const [fileId, setFileId] = useState<string>(scanned[0]?.file_id ?? "");
  const [view, setView] = useState<FileView | null>(null);
  const [mode, setMode] = useState<Mode>("reveal");
  const [error, setError] = useState<string | null>(null);
  const [groups, setGroups] = useState<Record<string, boolean>>({ invisible: true, confusable: true, comments: true, whitespace: true });
  const [showBenign, setShowBenign] = useState(false);
  const [range, setRange] = useState<{ from: string; to: string }>({ from: "", to: "" });
  const [focusLine, setFocusLine] = useState<number | null>(null);
  const lineRefs = useRef<Record<number, HTMLDivElement | null>>({});

  useEffect(() => {
    if (!target) return;
    const f = report.files.find((x) => x.relative_path === target.path);
    if (f) {
      setFileId(f.file_id);
      setFocusLine(target.line);
      setMode("reveal");
    }
  }, [target, report.files]);

  useEffect(() => {
    if (!fileId) return;
    setView(null);
    api.fileView(report.scan_id, fileId).then(setView).catch((e: Error) => setError(e.message));
  }, [fileId, report.scan_id]);

  useEffect(() => {
    if (focusLine && view) lineRefs.current[focusLine]?.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [focusLine, view, mode]);

  const enabledTypes = useMemo(
    () => new Set(Object.entries(groups).filter(([, on]) => on).flatMap(([g]) => TYPE_GROUPS[g])),
    [groups],
  );
  const anns = (view?.annotations ?? []).filter(
    (a) => enabledTypes.has(a.annotation_type) && (showBenign || a.severity !== "informational"),
  );
  const annotatedLines = new Set(anns.flatMap((a) => Array.from({ length: a.end_line - a.line + 1 }, (_, i) => a.line + i)));
  const from = parseInt(range.from) || 1;
  const to = parseInt(range.to) || Number.MAX_SAFE_INTEGER;

  const rawLines = view ? view.raw.split("\n") : [];

  return (
    <div className="split wide-left">
      <Card
        title={
          <label className="field inline">
            <span>File</span>
            <select value={fileId} onChange={(e) => { setFileId(e.target.value); setFocusLine(null); }}>
              {scanned.map((f) => <option key={f.file_id} value={f.file_id}>{f.relative_path}</option>)}
            </select>
          </label>
        }
        actions={
          <div className="seg" role="tablist" aria-label="View mode">
            {(["reveal", "raw", "preview"] as Mode[]).map((m) => (
              <button key={m} role="tab" aria-selected={mode === m} className={mode === m ? "on" : ""} onClick={() => setMode(m)}>
                {m === "reveal" ? "Reveal invisibles" : m === "raw" ? "Raw source" : "Rendered preview"}
              </button>
            ))}
          </div>
        }
      >
        <ErrorBox error={error} />
        <div className="filters">
          {Object.keys(TYPE_GROUPS).map((g) => (
            <label key={g} className="check">
              <input type="checkbox" checked={groups[g]} onChange={(e) => setGroups({ ...groups, [g]: e.target.checked })} /> {g}
            </label>
          ))}
          <label className="check">
            <input type="checkbox" checked={showBenign} onChange={(e) => setShowBenign(e.target.checked)} /> likely-benign
          </label>
          <label className="field inline small"><span>Lines</span>
            <input value={range.from} onChange={(e) => setRange({ ...range, from: e.target.value })} placeholder="from" inputMode="numeric" />
            <input value={range.to} onChange={(e) => setRange({ ...range, to: e.target.value })} placeholder="to" inputMode="numeric" />
          </label>
        </div>
        {!view ? (
          <p className="muted">Loading…</p>
        ) : mode === "preview" ? (
          <>
            <p className="note">{view.preview_note}</p>
            <pre className="preview">{view.preview}</pre>
          </>
        ) : (
          <>
            <p className="note">
              {mode === "raw"
                ? "Raw source exactly as uploaded (invisible characters are present but not visible). Compare with Reveal."
                : "Invisible characters shown as labels; comments/hidden HTML shaded; flagged trailing whitespace as · and ⇥; look-alike letters underlined."}
            </p>
            <div className="code" role="region" aria-label={`Source of ${view.relative_path}`} tabIndex={0}>
              {(mode === "raw" ? rawLines : view.reveal).map((line, i) => {
                const n = i + 1;
                if (n < from || n > to) return null;
                return (
                  <div
                    key={n}
                    ref={(el) => { lineRefs.current[n] = el; }}
                    className={`line ${annotatedLines.has(n) ? "annotated" : ""} ${focusLine === n ? "focus" : ""}`}
                  >
                    <span className="ln">{n}</span>
                    <span className="lc">
                      {typeof line === "string"
                        ? line
                        : line.map((seg, k) =>
                            seg.kind === "text" ? (
                              <span key={k}>{seg.text}</span>
                            ) : (
                              <span key={k} className={`seg-${seg.kind}`} title={seg.label}>{seg.text}</span>
                            ),
                          )}
                    </span>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </Card>

      <Card title={`Annotations (${anns.length})`}>
        <ul className="ann-list">
          {anns.map((a) => (
            <li key={a.annotation_id}>
              <button className="ann" onClick={() => { setFocusLine(a.line); setMode("reveal"); }}>
                <div className="row wrap">
                  <SeverityBadge severity={a.severity} />
                  <span className="tag">{a.annotation_type}</span>
                  <span className="muted">L{a.line}:{a.column}</span>
                </div>
                {a.unicode_name && <div><code>{a.unicode_name}</code></div>}
                {a.skeleton && <div className="muted">skeleton (comparison only): <code>{a.skeleton}</code></div>}
                <div className="muted small">{a.notes}</div>
                <code className="excerpt">{a.escaped_excerpt}</code>
              </button>
            </li>
          ))}
          {!anns.length && <li className="muted">No annotations for the selected filters.</li>}
        </ul>
      </Card>
    </div>
  );
}

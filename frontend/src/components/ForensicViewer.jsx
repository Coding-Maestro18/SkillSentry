import React, { useState, useEffect, useRef, useMemo } from "react";
import { Eye, FileCode } from "lucide-react";
import { api } from "../api/client";
import { Card, SeverityBadge } from "./CommonUI";

const TYPE_GROUPS = {
  invisible: ["invisible_char", "bidi_control", "tag_char"],
  confusable: ["confusable"],
  comments: ["html_comment", "hidden_html"],
  whitespace: ["whitespace_anomaly", "unusual_space"],
};

export function ForensicViewer({ report, target }) {
  const scannedFiles = useMemo(
    () => report.files.filter((f) => f.scanned),
    [report.files]
  );

  const [selectedFileId, setSelectedFileId] = useState(scannedFiles[0]?.file_id || "");
  const [fileViewData, setFileViewData] = useState(null);
  const [viewMode, setViewMode] = useState("reveal"); // 'reveal', 'raw', 'preview'
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [activeFilters, setActiveFilters] = useState({
    invisible: true,
    confusable: true,
    comments: true,
    whitespace: true,
    showBenign: false,
  });

  const [focusLine, setFocusLine] = useState(null);
  const [selectedAnnotation, setSelectedAnnotation] = useState(null);
  const lineRefs = useRef({});

  // When target changes (e.g. user clicked "View in Forensic Viewer" from FindingList)
  useEffect(() => {
    if (!target) return;
    const file = report.files.find((f) => f.relative_path === target.path);
    if (file) {
      setSelectedFileId(file.file_id);
      setFocusLine(target.line);
      setViewMode("reveal");
    }
  }, [target, report.files]);

  // Fetch file content & annotations
  useEffect(() => {
    if (!selectedFileId) return;
    setLoading(true);
    setError(null);
    setSelectedAnnotation(null);

    api.fileView(report.scan_id, selectedFileId)
      .then((data) => {
        setFileViewData(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [selectedFileId, report.scan_id]);

  // Scroll to focused line
  useEffect(() => {
    if (focusLine && lineRefs.current[focusLine]) {
      lineRefs.current[focusLine].scrollIntoView({ block: "center", behavior: "smooth" });
    }
  }, [focusLine, fileViewData, viewMode]);

  const enabledAnnotationTypes = useMemo(() => {
    const types = new Set();
    Object.entries(TYPE_GROUPS).forEach(([group, list]) => {
      if (activeFilters[group]) {
        list.forEach((t) => types.add(t));
      }
    });
    return types;
  }, [activeFilters]);

  const visibleAnnotations = useMemo(() => {
    if (!fileViewData) return [];
    return fileViewData.annotations.filter((ann) => {
      if (!enabledAnnotationTypes.has(ann.annotation_type)) return false;
      if (!activeFilters.showBenign && ann.severity === "informational") return false;
      return true;
    });
  }, [fileViewData, enabledAnnotationTypes, activeFilters.showBenign]);

  const annotatedLineMap = useMemo(() => {
    const map = new Map();
    visibleAnnotations.forEach((ann) => {
      for (let ln = ann.line; ln <= ann.end_line; ln++) {
        if (!map.has(ln)) map.set(ln, []);
        map.get(ln).push(ann);
      }
    });
    return map;
  }, [visibleAnnotations]);

  const rawLines = useMemo(() => {
    return fileViewData?.raw ? fileViewData.raw.split("\n") : [];
  }, [fileViewData]);

  return (
    <div className="flex flex-col gap-4">
      {/* File & Mode Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-[#0e1424] border border-slate-800 rounded-xl">
        <div className="flex items-center gap-2">
          <FileCode size={16} className="text-slate-400" />
          <span className="text-xs font-semibold text-slate-300">Inspecting File:</span>
          <select
            className="bg-[#0b0f1a] border border-slate-800 focus:border-blue-500 focus:outline-none rounded-md px-2.5 py-1 text-xs font-mono text-slate-200 cursor-pointer"
            value={selectedFileId}
            onChange={(e) => {
              setSelectedFileId(e.target.value);
              setFocusLine(null);
            }}
          >
            {scannedFiles.map((f) => (
              <option key={f.file_id} value={f.file_id}>
                {f.relative_path} ({f.size_bytes} bytes)
              </option>
            ))}
          </select>
        </div>

        {/* View Mode Toggle */}
        <div className="flex items-center gap-1 bg-[#0b0f1a] border border-slate-800 p-0.5 rounded-lg">
          <button
            type="button"
            className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium transition-colors cursor-pointer ${
              viewMode === "reveal"
                ? "bg-blue-600 text-white shadow-sm"
                : "text-slate-400 hover:text-slate-200"
            }`}
            onClick={() => setViewMode("reveal")}
          >
            <Eye size={13} />
            <span>Reveal Deception</span>
          </button>
          <button
            type="button"
            className={`px-3 py-1 rounded-md text-xs font-medium transition-colors cursor-pointer ${
              viewMode === "raw"
                ? "bg-blue-600 text-white shadow-sm"
                : "text-slate-400 hover:text-slate-200"
            }`}
            onClick={() => setViewMode("raw")}
          >
            <span>Raw Source</span>
          </button>
          <button
            type="button"
            className={`px-3 py-1 rounded-md text-xs font-medium transition-colors cursor-pointer ${
              viewMode === "preview"
                ? "bg-blue-600 text-white shadow-sm"
                : "text-slate-400 hover:text-slate-200"
            }`}
            onClick={() => setViewMode("preview")}
          >
            <span>Markdown Preview</span>
          </button>
        </div>
      </div>

      {/* Filter Toggles Bar for Reveal Mode */}
      {viewMode === "reveal" && (
        <div className="flex flex-wrap items-center gap-4 p-2.5 bg-[#0e1424] border border-slate-800 rounded-xl text-xs">
          <span className="font-semibold text-slate-400">Highlight Layers:</span>

          <label className="flex items-center gap-1.5 text-rose-300 cursor-pointer">
            <input
              type="checkbox"
              checked={activeFilters.invisible}
              onChange={(e) => setActiveFilters({ ...activeFilters, invisible: e.target.checked })}
              className="accent-rose-500 rounded"
            />
            <span>Zero-Width & Bidi</span>
          </label>

          <label className="flex items-center gap-1.5 text-amber-300 cursor-pointer">
            <input
              type="checkbox"
              checked={activeFilters.confusable}
              onChange={(e) => setActiveFilters({ ...activeFilters, confusable: e.target.checked })}
              className="accent-amber-500 rounded"
            />
            <span>Confusable Homoglyphs</span>
          </label>

          <label className="flex items-center gap-1.5 text-yellow-300 cursor-pointer">
            <input
              type="checkbox"
              checked={activeFilters.comments}
              onChange={(e) => setActiveFilters({ ...activeFilters, comments: e.target.checked })}
              className="accent-yellow-500 rounded"
            />
            <span>HTML Comments & CSS</span>
          </label>

          <label className="flex items-center gap-1.5 text-red-300 cursor-pointer">
            <input
              type="checkbox"
              checked={activeFilters.whitespace}
              onChange={(e) => setActiveFilters({ ...activeFilters, whitespace: e.target.checked })}
              className="accent-red-500 rounded"
            />
            <span>Anomalous Whitespace</span>
          </label>

          <label className="flex items-center gap-1.5 text-slate-400 ml-auto cursor-pointer">
            <input
              type="checkbox"
              checked={activeFilters.showBenign}
              onChange={(e) => setActiveFilters({ ...activeFilters, showBenign: e.target.checked })}
              className="accent-blue-500 rounded"
            />
            <span>Include Benign / Info</span>
          </label>
        </div>
      )}

      {/* Main Split: Code Viewer on Left, Annotation Inspector on Right */}
      <div className={`grid gap-4 items-start ${selectedAnnotation ? "grid-cols-1 lg:grid-cols-[1fr_340px]" : "grid-cols-1"}`}>
        {/* Left: Code Box */}
        <div className="bg-[#0e1424] border border-slate-800 rounded-xl overflow-hidden shadow-sm">
          {loading ? (
            <div className="p-12 text-center text-slate-500 text-xs">
              Loading file telemetry...
            </div>
          ) : error ? (
            <div className="m-4 p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-300 text-xs">
              {error}
            </div>
          ) : viewMode === "preview" ? (
            <div className="p-6 text-slate-200 leading-relaxed text-xs font-mono whitespace-pre-wrap">
              {fileViewData?.preview || fileViewData?.raw}
            </div>
          ) : (
            <div className="bg-[#070a12] border border-slate-800/80 rounded-lg font-mono text-[12px] leading-relaxed max-h-[680px] overflow-auto">
              {rawLines.map((lineText, idx) => {
                const lineNum = idx + 1;
                const lineAnns = annotatedLineMap.get(lineNum) || [];
                const isFocused = focusLine === lineNum;
                const isAnnotated = lineAnns.length > 0;

                return (
                  <div
                    key={lineNum}
                    ref={(el) => { lineRefs.current[lineNum] = el; }}
                    className={`flex min-w-full transition-colors ${
                      isAnnotated ? "bg-amber-500/5 hover:bg-amber-500/10 cursor-pointer" : "hover:bg-slate-800/20"
                    } ${isFocused ? "bg-blue-500/15 shadow-[inset_3px_0_0_#3b82f6]" : ""}`}
                    onClick={() => {
                      if (lineAnns.length > 0) {
                        setSelectedAnnotation(lineAnns[0]);
                      }
                    }}
                  >
                    <div className="shrink-0 w-14 text-right pr-3 pl-2 text-slate-600 select-none border-r border-slate-800/80">
                      {lineNum}
                    </div>
                    <div className="flex-1 px-3 whitespace-pre-wrap break-all text-slate-200">
                      {viewMode === "raw" ? (
                        lineText || " "
                      ) : (
                        renderAnnotatedLine(lineNum, lineText, lineAnns, (ann) => setSelectedAnnotation(ann))
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right: Selected Annotation Deep Inspector */}
        {selectedAnnotation && (
          <Card
            title="Code Point Telemetry"
            subtitle={`${selectedAnnotation.relative_path}:${selectedAnnotation.line}:${selectedAnnotation.column}`}
            actions={
              <button
                type="button"
                className="text-xs text-slate-400 hover:text-slate-200 px-2 py-0.5 rounded hover:bg-slate-800 cursor-pointer"
                onClick={() => setSelectedAnnotation(null)}
              >
                Close
              </button>
            }
          >
            <div className="space-y-3 text-xs">
              <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                <SeverityBadge severity={selectedAnnotation.severity} />
                <span className="font-mono text-[10px] text-slate-400 bg-slate-900 border border-slate-800 px-1.5 py-0.5 rounded">
                  {selectedAnnotation.detector_id}
                </span>
              </div>

              <dl className="grid grid-cols-[100px_1fr] gap-x-3 gap-y-2 font-mono m-0">
                <dt className="text-slate-400 font-sans">Annotation</dt>
                <dd className="font-bold text-rose-300 capitalize m-0">
                  {selectedAnnotation.annotation_type.replace(/_/g, " ")}
                </dd>

                {selectedAnnotation.code_point && (
                  <>
                    <dt className="text-slate-400 font-sans">Code Point</dt>
                    <dd className="text-slate-100 font-bold m-0">
                      {selectedAnnotation.code_point}{" "}
                      <span className="text-slate-400 font-normal">({selectedAnnotation.unicode_name})</span>
                    </dd>
                  </>
                )}

                <dt className="text-slate-400 font-sans">Offsets</dt>
                <dd className="text-slate-400 m-0">
                  Bytes {selectedAnnotation.start_offset} – {selectedAnnotation.end_offset}
                </dd>

                <dt className="text-slate-400 font-sans">Escaped</dt>
                <dd className="text-blue-300 break-all m-0">
                  <code>{selectedAnnotation.escaped_excerpt || "—"}</code>
                </dd>
              </dl>

              {selectedAnnotation.skeleton && (
                <div className="space-y-1 pt-2 border-t border-slate-800">
                  <span className="text-slate-400 font-medium">Comparison Skeleton:</span>
                  <div className="bg-[#070a12] border border-slate-800 p-2 rounded font-mono text-slate-200">
                    {selectedAnnotation.skeleton}
                  </div>
                </div>
              )}

              {selectedAnnotation.notes && (
                <div className="p-2.5 bg-[#070a12] border border-slate-800 rounded-lg text-slate-300 leading-relaxed text-[11px] mt-2">
                  {selectedAnnotation.notes}
                </div>
              )}
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}

function renderAnnotatedLine(lineNum, lineText, annotations, onSelect) {
  if (!annotations || annotations.length === 0) {
    return lineText || " ";
  }

  return (
    <span>
      {lineText}{" "}
      {annotations.map((ann, i) => (
        <span
          key={i}
          className="inline-flex items-center px-1.5 py-0.2 mx-0.5 rounded text-[10px] font-mono font-bold bg-rose-500/20 text-rose-300 border border-rose-500/40 cursor-pointer hover:bg-rose-500/30 transition-colors"
          onClick={(e) => {
            e.stopPropagation();
            onSelect(ann);
          }}
          title={`${ann.annotation_type}: ${ann.unicode_name || ann.code_point || ann.escaped_excerpt}`}
        >
          {ann.code_point || `[${ann.annotation_type}]`}
        </span>
      ))}
    </span>
  );
}

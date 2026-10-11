import { useEffect, useState } from "react";
import { api, waitForScan } from "./api/client";
import ScanProgress from "./components/ScanProgress";
import UploadPanel from "./components/UploadPanel";
import { ErrorBox } from "./components/ui";
import ReportPage from "./pages/ReportPage";
import type { Health, ScanReport, ScanStatus } from "./types";

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [status, setStatus] = useState<ScanStatus | null>(null);
  const [report, setReport] = useState<ScanReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.health().then(setHealth).catch((e: Error) => setHealthError(e.message));
    const id = new URLSearchParams(window.location.search).get("scan");
    if (id) void openScan(id);
  }, []);

  async function openScan(id: string) {
    setError(null);
    try {
      const done = await waitForScan(id, setStatus);
      if (done.status === "failed") {
        setError(done.error?.message ?? "Scan failed.");
        return;
      }
      setReport(await api.report(id));
      setStatus(null);
      window.history.replaceState(null, "", `?scan=${encodeURIComponent(id)}`);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function start(fn: () => Promise<ScanStatus>) {
    setBusy(true);
    setError(null);
    setReport(null);
    try {
      const s = await fn();
      setStatus(s);
      await openScan(s.scan_id);
    } catch (e) {
      setError((e as Error).message);
      setStatus(null);
    } finally {
      setBusy(false);
    }
  }

  function reset() {
    setReport(null);
    setStatus(null);
    setError(null);
    window.history.replaceState(null, "", window.location.pathname);
  }

  return (
    <div className="app">
      <header className="topbar">
        <button className="brand" onClick={reset} aria-label="SkillSentry home">
          <span className="logo" aria-hidden="true">◈</span> SkillSentry
        </button>
        <span className="muted">Security testing workbench for AI Agent Skills · analyze, simulate, never execute</span>
      </header>
      <main>
        <ErrorBox error={error} />
        {status && !report && <ScanProgress status={status} />}
        {!status && !report && (
          <UploadPanel
            health={health}
            healthError={healthError}
            busy={busy}
            onZip={(f) => start(() => api.uploadZip(f))}
            onText={(t) => start(() => api.pasteText(t))}
          />
        )}
        {report && <ReportPage report={report} onUpdate={setReport} onOpenScan={(id) => { setReport(null); void openScan(id); }} />}
      </main>
      <footer className="foot muted">
        SkillSentry v{health?.analyzer_version ?? "…"} · MIT License · Findings are triage signals, not proof of intent.
      </footer>
    </div>
  );
}

import React, { useEffect, useState } from "react";
import { api, waitForScan } from "./api/client";
import { Header } from "./components/Header";
import { UploadPanel } from "./components/UploadPanel";
import { ScanProgress } from "./components/ScanProgress";
import { ErrorAlert } from "./components/CommonUI";
import { ReportPage } from "./pages/ReportPage";
import { CampaignsPage } from "./components/CampaignsPage";

export default function App() {
  const [health, setHealth] = useState(null);
  const [healthError, setHealthError] = useState(null);
  const [scanStatus, setScanStatus] = useState(null);
  const [report, setReport] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);
  const [isBusy, setIsBusy] = useState(false);
  const [viewMode, setViewMode] = useState("audit"); // "audit" | "campaigns"

  const openExistingScan = async (scanId) => {
    setErrorMessage(null);
    try {
      const finalStatus = await waitForScan(scanId, setScanStatus);
      if (finalStatus.status === "failed") {
        setErrorMessage(finalStatus.error?.message || "Audit execution failed.");
        return;
      }
      const fullReport = await api.report(scanId);
      setReport(fullReport);
      setScanStatus(null);
      setViewMode("audit");
      window.history.replaceState(null, "", `?scan=${encodeURIComponent(scanId)}`);
    } catch (err) {
      setErrorMessage(err.message);
      setScanStatus(null);
    }
  };

  // Initial health check and URL scan param check
  useEffect(() => {
    api.health()
      .then(setHealth)
      .catch((err) => setHealthError(err.message));

    const params = new URLSearchParams(window.location.search);
    const initialScanId = params.get("scan");
    if (initialScanId) {
      void openExistingScan(initialScanId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const startScanJob = async (initiateCall) => {
    setIsBusy(true);
    setErrorMessage(null);
    setReport(null);
    setViewMode("audit");
    try {
      const initialStatus = await initiateCall();
      setScanStatus(initialStatus);
      await openExistingScan(initialStatus.scan_id);
    } catch (err) {
      setErrorMessage(err.message);
      setScanStatus(null);
    } finally {
      setIsBusy(false);
    }
  };

  const handleReset = () => {
    setReport(null);
    setScanStatus(null);
    setErrorMessage(null);
    setViewMode("audit");
    window.history.replaceState(null, "", window.location.pathname);
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#090d16] text-slate-100 font-sans selection:bg-blue-600 selection:text-white">
      <Header
        health={health}
        healthError={healthError}
        onReset={handleReset}
        hasActiveReport={!!report}
        isCampaignMode={viewMode === "campaigns"}
        onToggleCampaigns={() => setViewMode((m) => (m === "campaigns" ? "audit" : "campaigns"))}
      />

      <main className="flex-1 max-w-[1440px] w-full mx-auto px-4 sm:px-6 py-6 sm:py-8">
        <ErrorAlert message={errorMessage} onClose={() => setErrorMessage(null)} />

        {viewMode === "campaigns" ? (
          <CampaignsPage currentScanId={report?.scan_id} onOpenScan={openExistingScan} />
        ) : (
          <>
            {scanStatus && !report && <ScanProgress status={scanStatus} />}

            {!scanStatus && !report && (
              <UploadPanel
                health={health}
                healthError={healthError}
                busy={isBusy}
                onZip={(file) => startScanJob(() => api.uploadZip(file))}
                onText={(text) => startScanJob(() => api.pasteText(text))}
              />
            )}

            {report && (
              <ReportPage
                report={report}
                onUpdate={setReport}
                onOpenScan={(id) => {
                  setReport(null);
                  void openExistingScan(id);
                }}
              />
            )}
          </>
        )}
      </main>

      <footer className="border-t border-slate-800/80 px-4 py-4 text-center text-xs text-slate-500">
        SkillSentry · Findings are triage signals, not proof that a skill is safe.
      </footer>
    </div>
  );
}

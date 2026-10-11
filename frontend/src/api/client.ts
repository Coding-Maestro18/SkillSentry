import type {
  ApiErrorBody, Comparison, FileView, FixSuggestion, Health, ScanReport, ScanStatus, TestResult,
} from "../types";

export class ApiError extends Error {
  code: string;
  details: Record<string, unknown>;
  constructor(code: string, message: string, details: Record<string, unknown> = {}) {
    super(message);
    this.code = code;
    this.details = details;
  }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, init);
  } catch {
    throw new ApiError("NETWORK", "Cannot reach the SkillSentry API. Is the backend running on port 8000?");
  }
  if (!res.ok) {
    let body: ApiErrorBody | null = null;
    try {
      body = (await res.json()) as ApiErrorBody;
    } catch {
      /* non-JSON error */
    }
    throw new ApiError(body?.error.code ?? `HTTP_${res.status}`, body?.error.message ?? res.statusText, body?.error.details ?? {});
  }
  return (await res.json()) as T;
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  health: () => call<Health>("/api/health"),
  uploadZip: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return call<ScanStatus>("/api/scans", { method: "POST", body: fd });
  },
  pasteText: (text: string) => {
    const fd = new FormData();
    fd.append("skill_text", text);
    return call<ScanStatus>("/api/scans", { method: "POST", body: fd });
  },
  status: (id: string) => call<ScanStatus>(`/api/scans/${encodeURIComponent(id)}`),
  report: (id: string) => call<ScanReport>(`/api/scans/${encodeURIComponent(id)}/report`),
  fileView: (id: string, fileId: string) =>
    call<FileView>(`/api/scans/${encodeURIComponent(id)}/files/${encodeURIComponent(fileId)}/view`),
  runTest: (id: string, testId: string) =>
    call<TestResult>(`/api/scans/${encodeURIComponent(id)}/tests/${encodeURIComponent(testId)}/run`, { method: "POST" }),
  fix: (id: string, useModel: boolean, findingIds?: string[]) =>
    call<FixSuggestion>(`/api/scans/${encodeURIComponent(id)}/fix-suggestion`, json({ use_model: useModel, finding_ids: findingIds })),
  rerun: (id: string, files: Record<string, string>) =>
    call<ScanStatus>(`/api/scans/${encodeURIComponent(id)}/rerun`, json({ files })),
  comparison: (id: string) => call<Comparison>(`/api/scans/${encodeURIComponent(id)}/comparison`),
  exportUrl: (id: string, format: "json" | "markdown" | "sarif") => `/api/scans/${encodeURIComponent(id)}/export?format=${format}`,

  listScans: () => call<ScanStatus[]>("/api/scans"),

  // Policy (Feature C) - every saved policy is an immutable revision
  getPolicy: (id: string, revision?: number) =>
    call<any>(`/api/scans/${encodeURIComponent(id)}/policy${revision ? `?revision=${revision}` : ""}`),
  generatePolicy: (id: string) => call<any>(`/api/scans/${encodeURIComponent(id)}/policy/generate`, { method: "POST" }),
  validatePolicy: (id: string, yaml: string) =>
    call<any>(`/api/scans/${encodeURIComponent(id)}/policy/validate`, json({ yaml })),
  savePolicyRevision: (id: string, yaml: string) =>
    call<any>(`/api/scans/${encodeURIComponent(id)}/policy/revisions`, json({ yaml })),
  testPolicy: (id: string, revision: number) =>
    call<any>(`/api/scans/${encodeURIComponent(id)}/policy/test`, json({ revision })),
  policyExportUrl: (id: string, revision: number) =>
    `/api/scans/${encodeURIComponent(id)}/policy/export?revision=${revision}`,

  // Adaptive red team (Feature E)
  listRedTeamRuns: (id: string) => call<any[]>(`/api/scans/${encodeURIComponent(id)}/red-team-runs`),
  startRedTeam: (id: string) =>
    call<any>(`/api/scans/${encodeURIComponent(id)}/red-team-runs`, json({ advance_first_round: true })),
  advanceRedTeamRound: (runId: string) =>
    call<any>(`/api/red-team-runs/${encodeURIComponent(runId)}/advance`, { method: "POST" }),
  rerunRedTeam: (runId: string) =>
    call<any>(`/api/red-team-runs/${encodeURIComponent(runId)}/rerun`, { method: "POST" }),
  stopRedTeamRun: (runId: string) =>
    call<any>(`/api/red-team-runs/${encodeURIComponent(runId)}/stop`, { method: "POST" }),

  // Multi-skill campaigns (Feature A)
  listCampaigns: () => call<any[]>("/api/campaigns"),
  createCampaign: (data: { scan_ids: string[]; handoff_content?: string }) => call<any>("/api/campaigns", json(data)),
  simulateCampaign: (campaignId: string) =>
    call<any>(`/api/campaigns/${encodeURIComponent(campaignId)}/simulate`, { method: "POST" }),
  campaignSarifUrl: (campaignId: string) => `/api/campaigns/${encodeURIComponent(campaignId)}/export?format=sarif`,
};


export async function waitForScan(id: string, onStatus: (s: ScanStatus) => void): Promise<ScanStatus> {
  for (;;) {
    const s = await api.status(id);
    onStatus(s);
    if (s.status === "completed" || s.status === "failed") return s;
    await new Promise((r) => setTimeout(r, 600));
  }
}

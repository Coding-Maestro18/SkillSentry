import React, { useState, useEffect } from "react";
import { Network, Play, Download, ArrowRight } from "lucide-react";
import { api } from "../api/client";
import { Card, DecisionBadge, ErrorAlert, SeverityBadge } from "./CommonUI";
import { CanaryNote } from "./AttackLab";

const STATUS = {
  candidate: { label: "Candidate (not simulated)", cls: "text-slate-300 border-slate-600" },
  reproduced_in_simulation: { label: "Reproduced in simulation", cls: "text-rose-300 border-rose-500/40" },
  not_reproduced: { label: "Not reproduced", cls: "text-emerald-300 border-emerald-500/40" },
  needs_review: { label: "Needs review", cls: "text-amber-300 border-amber-500/40" },
};

const PROVENANCE = {
  observed: "observed",
  deterministic: "rule",
  model_hypothesis: "model",
  user_defined: "fixture",
  simulated_trace: "trace",
};

function NodeRow({ node, onOpenScan }) {
  const prov = <span className="text-[10px] text-slate-500 font-mono">{PROVENANCE[node.provenance] || node.provenance}</span>;
  if (node.node_type === "finding") {
    return (
      <button
        type="button"
        onClick={() => onOpenScan(node.scan_id)}
        title="Open this scan's report"
        className="w-full text-left flex items-start gap-2 p-2 rounded-md bg-[#070a12] border border-slate-800 hover:border-slate-600 cursor-pointer"
      >
        <SeverityBadge severity={node.metadata?.severity} />
        <span className="flex-1 text-slate-200">
          {node.label}
          <span className="block text-[10px] text-slate-500 font-mono">{node.finding_id} · {node.metadata?.location}</span>
        </span>
        {prov}
      </button>
    );
  }
  return (
    <div className="flex items-start gap-2 p-2 rounded-md bg-[#070a12] border border-slate-800">
      <span className="font-mono text-blue-400">{node.action_tool}</span>
      <DecisionBadge decision={node.metadata?.decision} />
      <span className="flex-1 text-[10px] text-slate-500">{node.metadata?.reason}</span>
      {prov}
    </div>
  );
}

function SkillColumn({ campaign, role, onOpenScan }) {
  const skill = campaign.nodes.find((n) => n.node_id === `skill-${role}`);
  const owned = new Set(
    campaign.edges.filter((e) => e.source_node_id === `skill-${role}`).map((e) => e.target_node_id)
  );
  const findings = campaign.nodes.filter((n) => n.node_type === "finding" && owned.has(n.node_id));
  const actions = campaign.nodes.filter((n) => n.node_type === "mock_action" && owned.has(n.node_id));
  if (!skill) return null;
  return (
    <div className="flex-1 min-w-[240px] space-y-2 text-xs">
      <div>
        <div className="text-[10px] uppercase text-slate-500 font-semibold">Skill {role.toUpperCase()}</div>
        <div className="text-sm font-semibold text-slate-100">{skill.label}</div>
        <div className="text-slate-500 font-mono text-[10px]">
          {skill.scan_id} · {skill.metadata?.files_scanned}/{skill.metadata?.file_count} files scanned
        </div>
        {skill.metadata?.description && <p className="text-slate-400 mt-1 mb-0">{skill.metadata.description}</p>}
      </div>
      {findings.length > 0 ? (
        findings.map((n) => <NodeRow key={n.node_id} node={n} onOpenScan={onOpenScan} />)
      ) : (
        <p className="text-slate-500 m-0">No findings.</p>
      )}
      {actions.length > 0 && (
        <>
          <div className="text-[10px] uppercase text-slate-500 font-semibold pt-1">Simulated actions</div>
          {actions.map((n) => <NodeRow key={n.node_id} node={n} onOpenScan={onOpenScan} />)}
        </>
      )}
    </div>
  );
}

export function CampaignsPage({ currentScanId, onOpenScan }) {
  const [scans, setScans] = useState([]);
  const [scanA, setScanA] = useState(currentScanId || "");
  const [scanB, setScanB] = useState("");
  const [handoff, setHandoff] = useState("");
  const [campaigns, setCampaigns] = useState([]);
  const [campaign, setCampaign] = useState(null);
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.listScans()
      .then((list) => setScans(list.filter((s) => s.status === "completed").reverse()))
      .catch((err) => setError(err.message));
    api.listCampaigns().then(setCampaigns).catch(() => {});
  }, []);

  const act = async (label, fn) => {
    setBusy(label);
    setError(null);
    try {
      const camp = await fn();
      setCampaign(camp);
      setCampaigns((prev) => [camp, ...prev.filter((c) => c.campaign_id !== camp.campaign_id)]);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(null);
    }
  };

  const scanLabel = (s) => `${s.skill_name || "Unnamed skill"} · ${s.scan_id}`;
  const select = "w-full bg-[#070a12] border border-slate-800 rounded-lg p-2 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500";
  const status = campaign && (STATUS[campaign.chain_status] || STATUS.candidate);
  const handoffNode = campaign?.nodes.find((n) => n.node_type === "handoff");
  const result = campaign?.results?.[0];

  return (
    <div className="flex flex-col gap-5">
      <ErrorAlert message={error} onClose={() => setError(null)} />

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-5 items-start">
        <Card title="New campaign" subtitle="Link two completed scans through a simulated handoff" icon={Network}>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <label className="space-y-1">
              <span className="text-slate-400">Skill A (produces the handoff)</span>
              <select className={select} value={scanA} onChange={(e) => setScanA(e.target.value)}>
                <option value="">Select a scan…</option>
                {scans.map((s) => <option key={s.scan_id} value={s.scan_id}>{scanLabel(s)}</option>)}
              </select>
            </label>
            <label className="space-y-1">
              <span className="text-slate-400">Skill B (consumes it)</span>
              <select className={select} value={scanB} onChange={(e) => setScanB(e.target.value)}>
                <option value="">Select a scan…</option>
                {scans.filter((s) => s.scan_id !== scanA).map((s) => (
                  <option key={s.scan_id} value={s.scan_id}>{scanLabel(s)}</option>
                ))}
              </select>
            </label>
            <label className="space-y-1 sm:col-span-2">
              <span className="text-slate-400">Handoff content (optional, inert text)</span>
              <input
                className={select}
                value={handoff}
                maxLength={2000}
                onChange={(e) => setHandoff(e.target.value)}
                placeholder="Simulated intermediate research summary produced by Skill A."
              />
            </label>
          </div>
          <div className="flex items-center justify-between mt-4">
            <span className="text-[11px] text-slate-500">
              {scans.length < 2 ? "Scan at least two skills first." : "Neither skill is executed; only mock tools are used."}
            </span>
            <button
              type="button"
              disabled={!scanA || !scanB || !!busy}
              onClick={() => act("create", () => api.createCampaign({ scan_ids: [scanA, scanB], handoff_content: handoff || undefined }))}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold cursor-pointer disabled:opacity-50"
            >
              <Network size={13} /> {busy === "create" ? "Creating…" : "Create campaign"}
            </button>
          </div>
        </Card>

        <Card title="Saved campaigns">
          {campaigns.length === 0 ? (
            <p className="text-xs text-slate-500 m-0">None yet.</p>
          ) : (
            <div className="space-y-1.5 max-h-60 overflow-y-auto">
              {campaigns.map((c) => (
                <button
                  key={c.campaign_id}
                  type="button"
                  onClick={() => setCampaign(c)}
                  className={`w-full text-left p-2 rounded-md border text-xs cursor-pointer ${
                    campaign?.campaign_id === c.campaign_id
                      ? "bg-blue-600/15 border-blue-500/40"
                      : "bg-[#070a12] border-slate-800 hover:border-slate-600"
                  }`}
                >
                  <div className="text-slate-200 truncate">{c.campaign_name}</div>
                  <div className="text-[10px] text-slate-500">{(STATUS[c.chain_status] || STATUS.candidate).label}</div>
                </button>
              ))}
            </div>
          )}
        </Card>
      </div>

      {campaign && (
        <Card
          title={campaign.campaign_name}
          subtitle={campaign.campaign_id}
          actions={
            <div className="flex items-center gap-2">
              <span className={`text-[11px] font-semibold px-2 py-0.5 rounded border ${status.cls}`}>{status.label}</span>
              <a
                href={api.campaignSarifUrl(campaign.campaign_id)}
                download
                title="Source-anchored findings from both skills (download only)"
                className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-md text-xs text-slate-200"
              >
                <Download size={12} /> SARIF
              </a>
              <button
                type="button"
                disabled={!!busy}
                onClick={() => act("sim", () => api.simulateCampaign(campaign.campaign_id))}
                className="inline-flex items-center gap-1.5 px-3 py-1 bg-rose-600 hover:bg-rose-500 text-white rounded-md text-xs font-semibold cursor-pointer disabled:opacity-50"
              >
                <Play size={12} /> {busy === "sim" ? "Simulating…" : campaign.results?.length ? "Re-simulate" : "Simulate chain"}
              </button>
            </div>
          }
        >
          <div className="space-y-4">
            <p className="text-xs text-slate-400 m-0">{campaign.status_detail}</p>

            <div className="flex flex-col md:flex-row gap-4 items-stretch">
              <SkillColumn campaign={campaign} role="a" onOpenScan={onOpenScan} />
              <div className="flex md:flex-col items-center justify-center gap-2 text-xs text-slate-400 md:w-48">
                <ArrowRight size={16} className="md:hidden" />
                <div className="p-2.5 rounded-md border border-purple-500/30 bg-purple-500/5 text-center">
                  <div className="text-[10px] uppercase text-purple-300 font-semibold">Handoff · fixture</div>
                  <div className="text-slate-300 mt-1 break-words">{campaign.handoff_fixture_content}</div>
                  <div className="text-[10px] text-slate-500 font-mono mt-1">{handoffNode?.fixture_id}</div>
                </div>
                <ArrowRight size={16} className="hidden md:block" />
              </div>
              <SkillColumn campaign={campaign} role="b" onOpenScan={onOpenScan} />
            </div>

            {result && <CanaryNote event={result.canary_event} />}
            <p className="text-[11px] text-slate-500 m-0">
              Labels: rule = deterministic finding · fixture = user-defined handoff · trace = recorded mock-harness event.
              Simulated with fixtures and mock tools only; not a guaranteed path in a real agent runtime.
            </p>
          </div>
        </Card>
      )}
    </div>
  );
}

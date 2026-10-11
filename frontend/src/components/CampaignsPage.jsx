import React, { useState, useEffect } from "react";
import {
  Network,
  Play,
  Shield,
  Layers,
  ArrowRight,
  AlertTriangle,
  CheckCircle2,
  FileText,
  RotateCcw,
  Hash,
} from "lucide-react";
import { api } from "../api/client";
import { Card, DecisionBadge } from "./CommonUI";

export function CampaignsPage({ currentScanId, onBack, onOpenScan }) {
  const [scanIdA, setScanIdA] = useState(currentScanId || "");
  const [scanIdB, setScanIdB] = useState("");
  const [handoffFixture, setHandoffFixture] = useState("handoff_fixture_001");
  const [handoffContent, setHandoffContent] = useState("Simulated research report containing extracted canary tokens.");
  const [campaign, setCampaign] = useState(null);
  const [campaignList, setCampaignList] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSimulating, setIsSimulating] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.listCampaigns().then(setCampaignList).catch(() => {});
  }, []);

  const handleCreate = async () => {
    if (!scanIdA.trim() || !scanIdB.trim()) {
      setError("Please specify two completed scan IDs.");
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const camp = await api.createCampaign({
        scan_ids: [scanIdA.trim(), scanIdB.trim()],
        handoff_fixture_id: handoffFixture,
        handoff_content: handoffContent,
      });
      setCampaign(camp);
      setCampaignList((prev) => [camp, ...prev.filter((c) => c.campaign_id !== camp.campaign_id)]);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSimulate = async () => {
    if (!campaign) return;
    setIsSimulating(true);
    setError(null);
    try {
      const updated = await api.simulateCampaign(campaign.campaign_id);
      setCampaign(updated);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSimulating(false);
    }
  };

  const handleSelectCampaign = async (cid) => {
    setIsLoading(true);
    setError(null);
    try {
      const camp = await api.getCampaign(cid);
      setCampaign(camp);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-6 max-w-[1440px] mx-auto w-full">
      {/* Simulation Disclaimer Banner */}
      <div className="p-3.5 bg-blue-500/10 border border-blue-500/25 rounded-xl text-blue-200 text-xs flex items-center gap-3">
        <Shield size={18} className="shrink-0 text-blue-400" />
        <div>
          <strong>Multi-Skill Campaign Simulation:</strong> Cross-skill interactions are evaluated strictly through explicit fixtures and allowlisted mock tools.
          Neither skill code is executed on the host, and no external network sockets are opened.
        </div>
      </div>

      {error && (
        <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-300 text-xs flex items-center gap-2">
          <AlertTriangle size={15} />
          <span>{error}</span>
        </div>
      )}

      {/* Top Controls: Setup or Load Campaign */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2">
          <Card
            title="Create Multi-Skill Attack Chain"
            subtitle="Connect two independently audited skills with an explicit simulated handoff fixture"
            icon={Network}
          >
            <div className="space-y-4 text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 font-medium mb-1">Source Skill (Skill A - Scan ID)</label>
                  <input
                    type="text"
                    value={scanIdA}
                    onChange={(e) => setScanIdA(e.target.value)}
                    placeholder="e.g. scan_abc123456789"
                    className="w-full font-mono text-xs p-2.5 bg-[#070a12] border border-slate-800 rounded-lg text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 font-medium mb-1">Target Skill (Skill B - Scan ID)</label>
                  <input
                    type="text"
                    value={scanIdB}
                    onChange={(e) => setScanIdB(e.target.value)}
                    placeholder="e.g. scan_def987654321"
                    className="w-full font-mono text-xs p-2.5 bg-[#070a12] border border-slate-800 rounded-lg text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 font-medium mb-1">Handoff Fixture Identifier</label>
                  <input
                    type="text"
                    value={handoffFixture}
                    onChange={(e) => setHandoffFixture(e.target.value)}
                    className="w-full font-mono text-xs p-2.5 bg-[#070a12] border border-slate-800 rounded-lg text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 font-medium mb-1">Handoff Fixture Content</label>
                  <input
                    type="text"
                    value={handoffContent}
                    onChange={(e) => setHandoffContent(e.target.value)}
                    className="w-full text-xs p-2.5 bg-[#070a12] border border-slate-800 rounded-lg text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div className="flex items-center justify-between pt-2">
                <button
                  type="button"
                  onClick={handleCreate}
                  disabled={isLoading}
                  className="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold transition-colors cursor-pointer disabled:opacity-50"
                >
                  <Network size={14} />
                  <span>{isLoading ? "Assembling Graph..." : "Construct Campaign Graph"}</span>
                </button>

                <button
                  type="button"
                  onClick={onBack}
                  className="text-xs text-slate-400 hover:text-slate-200 underline cursor-pointer"
                >
                  ← Return to Audit Overview
                </button>
              </div>
            </div>
          </Card>
        </div>

        {/* Saved Campaigns Sidebar */}
        <div>
          <Card
            title="Saved Campaigns"
            subtitle={`${campaignList.length} campaign(s) stored`}
            icon={Layers}
          >
            {campaignList.length === 0 ? (
              <p className="text-xs text-slate-500 italic m-0">No multi-skill campaigns saved yet.</p>
            ) : (
              <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                {campaignList.map((c) => (
                  <button
                    key={c.campaign_id}
                    type="button"
                    onClick={() => handleSelectCampaign(c.campaign_id)}
                    className={`w-full text-left p-2.5 rounded-lg border text-xs transition-colors cursor-pointer ${
                      campaign?.campaign_id === c.campaign_id
                        ? "bg-blue-600/15 border-blue-500/40 text-blue-200"
                        : "bg-[#070a12] border-slate-800 text-slate-300 hover:bg-slate-800/40"
                    }`}
                  >
                    <div className="font-semibold text-xs truncate">{c.campaign_name}</div>
                    <div className="font-mono text-[10px] text-slate-400 mt-0.5">
                      {c.campaign_id} · <span className="uppercase text-amber-400">{c.chain_status}</span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>

      {/* Campaign Details & Attack Chain Graph Viewer */}
      {campaign && (
        <div className="space-y-6">
          {/* Campaign Header Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 p-4 bg-[#0e1424] border border-slate-800 rounded-xl">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-slate-100 m-0">{campaign.campaign_name}</h3>
                <span className={`text-[11px] font-semibold uppercase px-2.5 py-0.5 rounded-full border ${
                  campaign.chain_status === "reproduced_in_simulation"
                    ? "bg-rose-500/15 text-rose-300 border-rose-500/30"
                    : "bg-blue-500/15 text-blue-300 border-blue-500/30"
                }`}>
                  Status: {campaign.chain_status}
                </span>
              </div>
              <span className="font-mono text-xs text-slate-400">
                Campaign ID: {campaign.campaign_id} · Scans: {campaign.scan_ids.join(" & ")}
              </span>
            </div>

            <button
              type="button"
              onClick={handleSimulate}
              disabled={isSimulating}
              className="inline-flex items-center gap-2 px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-xs font-semibold transition-colors cursor-pointer disabled:opacity-50 shadow-md shadow-rose-950/40"
            >
              <Play size={14} />
              <span>{isSimulating ? "Simulating Chain..." : "Simulate Attack Chain"}</span>
            </button>
          </div>

          {/* Graph Representation */}
          <Card
            title="Attack Chain Graph Representation"
            subtitle="Cross-skill relationships, findings, handoff fixtures, and mock traces"
            icon={Network}
          >
            <div className="space-y-5">
              {/* Nodes Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                {campaign.nodes.map((node) => {
                  let badgeColor = "bg-slate-800 text-slate-300 border-slate-700";
                  if (node.node_type === "skill") badgeColor = "bg-blue-500/15 text-blue-300 border-blue-500/30";
                  if (node.node_type === "finding") badgeColor = "bg-amber-500/15 text-amber-300 border-amber-500/30";
                  if (node.node_type === "handoff") badgeColor = "bg-purple-500/15 text-purple-300 border-purple-500/30";
                  if (node.node_type === "mock_action") badgeColor = "bg-rose-500/15 text-rose-300 border-rose-500/30";
                  if (node.node_type === "canary_match") badgeColor = "bg-emerald-500/15 text-emerald-300 border-emerald-500/30";

                  return (
                    <div
                      key={node.node_id}
                      className="p-3 bg-[#070a12] border border-slate-800 rounded-lg text-xs space-y-1.5"
                    >
                      <div className="flex items-center justify-between">
                        <span className={`text-[10px] uppercase font-mono px-2 py-0.5 rounded-full border ${badgeColor}`}>
                          {node.node_type}
                        </span>
                        <span className="font-mono text-[10px] text-slate-500">
                          {node.provenance}
                        </span>
                      </div>
                      <div className="font-semibold text-slate-200 text-xs">{node.label}</div>
                      {node.scan_id && (
                        <div className="font-mono text-[10px] text-slate-400">
                          Scan: {node.scan_id}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Edges List */}
              <div className="border-t border-slate-800 pt-3">
                <h4 className="text-xs font-semibold text-slate-300 mb-2">Connected Relationships ({campaign.edges.length} Edges)</h4>
                <div className="flex flex-wrap gap-2">
                  {campaign.edges.map((edge, i) => (
                    <div
                      key={i}
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-[#0b101d] border border-slate-800 rounded text-[11px] text-slate-300 font-mono"
                    >
                      <span className="text-blue-400">{edge.source_node_id}</span>
                      <ArrowRight size={11} className="text-slate-500" />
                      <span className="text-amber-400">{edge.target_node_id}</span>
                      <span className="text-slate-500 font-sans text-[10px]">({edge.edge_type})</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </Card>

          {/* Simulation Results & Traces */}
          {campaign.results?.length > 0 && (
            <Card
              title="Chain Simulation Outcome & Traces"
              subtitle="Mock harness execution of composite handoff exfiltration test"
              icon={Layers}
            >
              <div className="space-y-4">
                {campaign.results.map((res, i) => (
                  <div key={i} className="space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-2 p-3 bg-[#070a12] border border-slate-800 rounded-lg text-xs">
                      <span className="text-slate-300">
                        Summary: <strong className="text-slate-100">{res.summary}</strong>
                      </span>
                      <span className="text-emerald-400 font-semibold font-mono text-[11px]">
                        Status: {res.status.toUpperCase()}
                      </span>
                    </div>

                    {res.canary_event && (
                      <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-emerald-200 text-xs flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Hash size={15} className="text-emerald-400" />
                          <span>
                            <strong>Canary Exfiltration Detected:</strong> Synthetic token passed through handoff and observed in mock request.
                          </span>
                        </div>
                        <span className="font-mono text-[10px] text-emerald-300">
                          Digest: {res.canary_event.token_digest}
                        </span>
                      </div>
                    )}

                    {/* Trace Events Table */}
                    <div className="overflow-x-auto border border-slate-800 rounded-lg">
                      <table className="w-full text-left border-collapse text-xs">
                        <thead>
                          <tr className="bg-[#0b101d] text-slate-400 border-b border-slate-800">
                            <th className="py-2 px-3 font-medium">Step</th>
                            <th className="py-2 px-3 font-medium">Tool</th>
                            <th className="py-2 px-3 font-medium">Arguments</th>
                            <th className="py-2 px-3 font-medium">Policy Decision</th>
                            <th className="py-2 px-3 font-medium">Mock Output</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/60 bg-[#070a12]">
                          {res.events.map((ev, idx) => (
                            <tr key={idx} className="hover:bg-slate-800/20">
                              <td className="py-2 px-3 font-mono text-slate-500 text-[11px]">{ev.sequence_number}</td>
                              <td className="py-2 px-3 font-mono font-medium text-blue-400 text-[11px]">{ev.tool_name}</td>
                              <td className="py-2 px-3 font-mono text-[11px] text-slate-300">
                                {Object.entries(ev.sanitized_arguments).map(([k, v]) => (
                                  <div key={k}>{k}: {v}</div>
                                ))}
                              </td>
                              <td className="py-2 px-3">
                                <DecisionBadge decision={ev.policy_decision} />
                              </td>
                              <td className="py-2 px-3 font-mono text-slate-400 text-[11px]">
                                {ev.mock_result_summary}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}

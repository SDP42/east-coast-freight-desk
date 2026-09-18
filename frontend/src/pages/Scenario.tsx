import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { FlaskConical, ArrowRight, Repeat, Waves } from "lucide-react";
import SpotlightCard from "../components/SpotlightCard";
import { getPorts, runScenario, type Port, type ScenarioResult, type Shock } from "../lib/api";

export default function Scenario() {
  const [ports, setPorts] = useState<Port[]>([]);
  const [portId, setPortId] = useState<number | null>(null);
  const [tonnes, setTonnes] = useState("75000");
  const [spikeOn, setSpikeOn] = useState(true);
  const [spikePct, setSpikePct] = useState(50);
  const [closureOn, setClosureOn] = useState(false);
  const [closureDays, setClosureDays] = useState(3);
  const [redSea, setRedSea] = useState(true);
  const [result, setResult] = useState<ScenarioResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getPorts()
      .then((p) => {
        setPorts(p);
        setPortId(p.find((x) => x.name === "Paradip")?.id ?? p[0]?.id ?? null);
      })
      .catch(() => setError("Could not load ports — is the backend running?"));
  }, []);

  async function run() {
    if (portId == null) return;
    const shocks: Shock[] = [];
    if (spikeOn) shocks.push({ type: "freight_spike", pct: spikePct });
    if (closureOn) shocks.push({ type: "port_closure", days: closureDays });
    if (redSea) shocks.push({ type: "red_sea_closure" });
    setLoading(true);
    setError(null);
    try {
      setResult(await runScenario(portId, Number(tonnes), shocks));
    } catch {
      setError("Scenario failed — check inputs or backend status.");
    } finally {
      setLoading(false);
    }
  }

  const fmt = (n: number | null) => (n == null ? "—" : `$${(n / 1000).toLocaleString(undefined, { maximumFractionDigits: 0 })}k`);

  return (
    <div className="space-y-6">
      <motion.h1 initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="text-2xl font-bold text-white">
        Scenario Sandbox
      </motion.h1>

      <SpotlightCard>
        <div className="p-6">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-white">
            <FlaskConical className="h-4 w-4 text-cyan" /> Stress-test the recommendation
          </h2>
          <p className="mt-1 text-xs text-muted">Apply shocks and see how the ranking, costs, and best origin change.</p>

          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <label className="text-xs text-muted">
              Destination port
              <select className="mt-1 w-full rounded-md border border-border-soft bg-panel-light px-3 py-2 text-sm text-white" value={portId ?? ""} onChange={(e) => setPortId(Number(e.target.value))}>
                {ports.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </label>
            <label className="text-xs text-muted">
              Cargo tonnage
              <input className="mt-1 w-full rounded-md border border-border-soft bg-panel-light px-3 py-2 text-sm text-white" value={tonnes} onChange={(e) => setTonnes(e.target.value)} />
            </label>
          </div>

          <div className="mt-5 space-y-4">
            <div className="rounded-lg border border-border-soft bg-panel-light/40 p-4">
              <label className="flex items-center gap-2 text-sm text-white">
                <input type="checkbox" checked={spikeOn} onChange={(e) => setSpikeOn(e.target.checked)} /> Freight rate spike
                <span className="ml-auto font-semibold text-amber">{spikePct >= 0 ? "+" : ""}{spikePct}%</span>
              </label>
              <input type="range" min={-30} max={150} value={spikePct} onChange={(e) => setSpikePct(Number(e.target.value))} disabled={!spikeOn} className="mt-2 w-full accent-cyan" />
            </div>

            <div className="rounded-lg border border-border-soft bg-panel-light/40 p-4">
              <label className="flex items-center gap-2 text-sm text-white">
                <input type="checkbox" checked={closureOn} onChange={(e) => setClosureOn(e.target.checked)} /> Destination port closure
                <span className="ml-auto font-semibold text-amber">{closureDays} days</span>
              </label>
              <input type="range" min={1} max={14} value={closureDays} onChange={(e) => setClosureDays(Number(e.target.value))} disabled={!closureOn} className="mt-2 w-full accent-cyan" />
            </div>

            <div className="rounded-lg border border-border-soft bg-panel-light/40 p-4">
              <label className="flex items-center gap-2 text-sm text-white">
                <input type="checkbox" checked={redSea} onChange={(e) => setRedSea(e.target.checked)} /> Red Sea closure
                <span className="ml-auto text-xs text-muted">+3,500 nm for Russia &amp; US routes</span>
              </label>
            </div>
          </div>

          <button onClick={run} disabled={loading || portId == null} className="mt-5 rounded-md bg-cyan/90 px-4 py-2 text-sm font-medium text-navy transition hover:bg-cyan disabled:opacity-50">
            {loading ? "Running scenario…" : "Run scenario"}
          </button>
          {error && <p className="mt-3 text-sm text-down">{error}</p>}
        </div>
      </SpotlightCard>

      {result && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
          <SpotlightCard glowColor={result.best_origin_changed ? "251,191,36" : "52,211,153"}>
            <div className="p-5">
              <p className="text-xs uppercase tracking-wide text-muted">{result.shocks_applied.join(" · ") || "No shocks"}</p>
              <p className="mt-2 text-sm font-medium text-white">{result.summary}</p>
            </div>
          </SpotlightCard>

          <SpotlightCard glowColor="203,213,225">
            <div className="overflow-x-auto p-2">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase tracking-wide text-muted">
                    <th className="px-4 py-3 font-medium">Origin</th>
                    <th className="px-4 py-3 font-medium">Baseline</th>
                    <th className="px-4 py-3 font-medium" />
                    <th className="px-4 py-3 font-medium">Scenario</th>
                    <th className="px-4 py-3 font-medium">Change</th>
                    <th className="px-4 py-3 font-medium">Rank</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-soft/60">
                  {result.origins.map((o) => (
                    <tr key={o.origin_country} className="hover:bg-panel-light/60">
                      <td className="px-4 py-3 font-medium text-white">{o.origin_country}</td>
                      <td className="px-4 py-3 text-ice/90">{fmt(o.baseline_cost_usd)}</td>
                      <td className="px-4 py-3"><ArrowRight className="h-3.5 w-3.5 text-muted" /></td>
                      <td className="px-4 py-3 text-white">{fmt(o.scenario_cost_usd)}</td>
                      <td className={`px-4 py-3 ${(o.delta_pct ?? 0) > 0 ? "text-down" : "text-up"}`}>{o.delta_pct != null ? `${o.delta_pct > 0 ? "+" : ""}${o.delta_pct}%` : "—"}</td>
                      <td className="px-4 py-3 text-muted">
                        #{o.baseline_rank}
                        {o.baseline_rank !== o.scenario_rank && <span className="text-amber"> → #{o.scenario_rank}</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </SpotlightCard>

          {result.reroute_alternatives.length > 0 && (
            <SpotlightCard glowColor="251,191,36">
              <div className="p-5">
                <h3 className="flex items-center gap-2 text-sm font-semibold text-white">
                  <Repeat className="h-4 w-4 text-amber" /> Reroute alternatives (port closure)
                </h3>
                <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-3">
                  {result.reroute_alternatives.map((r) => (
                    <div key={r.port_name} className="rounded-md border border-border-soft bg-panel-light/50 p-3 text-xs">
                      <p className="flex items-center gap-1.5 font-medium text-white"><Waves className="h-3.5 w-3.5 text-cyan" />{r.port_name}</p>
                      <p className="mt-1 text-muted">via {r.best_origin} · {fmt(r.estimated_total_cost_usd)}</p>
                      <p className="mt-1 font-semibold text-up">saves {fmt(r.savings_vs_scenario_best_usd)}</p>
                    </div>
                  ))}
                </div>
              </div>
            </SpotlightCard>
          )}
        </motion.div>
      )}
    </div>
  );
}

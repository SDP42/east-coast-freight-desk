import { useState } from "react";
import { Scale } from "lucide-react";
import SpotlightCard from "./SpotlightCard";
import { Note, btnCls, errText } from "./ui";
import { api } from "../lib/api";

interface Option { origin: string; cost: number; days: number; risk: number; vessel_class: string; fits_berth: boolean; dominated_by: string[]; pareto: boolean; score: number; rank: number }
interface Res { options: Option[]; weights: { cost: number; time: number; risk: number }; note: string; port: string }

/** Multi-objective view: cost, transit time and route risk together; Pareto-optimal origins are marked. */
export default function ParetoCard({ portId, cargoTonnes }: { portId: number | null; cargoTonnes: number }) {
  const [wc, setWc] = useState(50);
  const [wt, setWt] = useState(25);
  const [wr, setWr] = useState(25);
  const [res, setRes] = useState<Res | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  async function run() {
    if (portId == null) return;
    setBusy(true); setErr("");
    try { setRes((await api.post<Res>("/recommendation/pareto", { destination_port_id: portId, cargo_tonnes: cargoTonnes, w_cost: wc, w_time: wt, w_risk: wr })).data); } catch (e) { setErr(errText(e)); } finally { setBusy(false); }
  }
  const slider = (label: string, v: number, set: (n: number) => void) => (
    <label className="block text-xs font-medium text-body">{label}: {v}%<input type="range" min={0} max={100} value={v} onChange={(e) => set(Number(e.target.value))} className="mt-1 w-full accent-cyan" /></label>
  );
  return (
    <SpotlightCard>
      <div className="p-6">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-strong"><Scale className="h-4 w-4 text-cyan" /> Trade-offs: cost, time and risk together</h2>
        <p className="mt-1 text-xs text-muted">An origin is Pareto-optimal if no other origin beats it on all three at once. Set what matters most and see the ranking change.</p>
        <div className="mt-4 grid gap-4 sm:grid-cols-4">
          {slider("Cost", wc, setWc)}{slider("Transit time", wt, setWt)}{slider("Route risk", wr, setWr)}
          <div className="flex items-end"><button className={btnCls + " w-full"} onClick={run} disabled={busy || portId == null}>{busy ? "Ranking…" : "Rank origins"}</button></div>
        </div>
        {err && <p className="mt-3 text-xs text-down">{err}</p>}
        {res && (
          <div className="mt-5 space-y-3">
            <table className="w-full text-left text-sm">
              <thead><tr className="text-xs text-muted"><th className="py-1">#</th><th>Origin</th><th>Cost $/t</th><th>Days</th><th>Risk /10</th><th>Score</th><th></th></tr></thead>
              <tbody>{res.options.map((o) => (
                <tr key={o.origin} className="border-t border-border-soft">
                  <td className="py-1.5 font-semibold text-strong">{o.rank}</td>
                  <td className="font-medium text-strong">{o.origin}{!o.fits_berth && <span className="ml-2 rounded bg-down/10 px-1.5 text-[10px] text-down">vessel does not fit</span>}</td>
                  <td>{o.cost.toFixed(2)}</td><td>{o.days}</td><td>{o.risk.toFixed(1)}</td><td>{o.score.toFixed(2)}</td>
                  <td>{o.pareto ? <span className="rounded-full bg-up/10 px-2 py-0.5 text-[10px] font-medium text-up">Pareto-optimal</span> : <span className="text-[11px] text-muted">beaten by {o.dominated_by.join(", ")}</span>}</td>
                </tr>
              ))}</tbody>
            </table>
            <Note>{res.note}</Note>
          </div>
        )}
      </div>
    </SpotlightCard>
  );
}

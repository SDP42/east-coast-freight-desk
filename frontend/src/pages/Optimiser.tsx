import { useEffect, useState } from "react";
import SpotlightCard from "../components/SpotlightCard";
import Loading from "../components/Loading";
import { Note, PageHeader, Stat, errText, Fine } from "../components/ui";
import { api } from "../lib/api";

interface Alloc { origin: string; port: string; plant: string; kt: number; landed_inr_per_t: number }
interface Bind { limit: string; used_kt: number; limit_kt: number; saving_inr_lakh_per_extra_kt_per_month: number }
interface Res {
  feasible: boolean; message?: string; monthly_cost_inr_crore: number; baseline_cost_inr_crore: number | null; saving_inr_crore_per_month: number; saving_pct: number; saving_inr_crore_per_year: number;
  avg_landed_inr_per_t: number; allocation: Alloc[]; by_origin_kt: Record<string, number>; by_port_kt: Record<string, number>; hhi: number; binding_limits: Bind[]; method: string; total_demand_kt: number;
}

export default function Optimiser() {
  const [r, setR] = useState<Res | null>(null);
  const [err, setErr] = useState("");
  useEffect(() => { api.post<Res>("/sourcing/optimise", {}).then((x) => setR(x.data)).catch((e) => setErr(errText(e))); }, []);
  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader title="Sourcing optimiser" subtitle="The cheapest origin, port and plant mix for the month, and what each limit costs." />
      {err && <p className="text-xs text-down">{err}</p>}
      {!r && !err && <Loading label="Solving the allocation" pattern="sweep" block />}
      {r && !r.feasible && <Note kind="warn">{r.message}</Note>}
      {r && r.feasible && (
        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-4">
            <Stat label="Monthly cost" value={`₹${r.monthly_cost_inr_crore} cr`} /><Stat label="Saving vs current mix" value={`₹${r.saving_inr_crore_per_month} cr (${r.saving_pct}%)`} tone="up" />
            <Stat label="Per year" value={`₹${r.saving_inr_crore_per_year} cr`} tone="up" /><Stat label="Average landed" value={`₹${r.avg_landed_inr_per_t}/t`} />
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <SpotlightCard><div className="p-5"><h3 className="text-sm font-semibold text-strong">By origin (kt per month)</h3><ul className="mt-2 space-y-1 text-sm text-body">{Object.entries(r.by_origin_kt).map(([k, v]) => <li key={k} className="flex justify-between"><span>{k}</span><span className="font-medium text-strong">{v}</span></li>)}</ul><p className="mt-2 text-xs text-muted">Concentration (HHI) {r.hhi}</p></div></SpotlightCard>
            <SpotlightCard><div className="p-5"><h3 className="text-sm font-semibold text-strong">By port (kt per month)</h3><ul className="mt-2 space-y-1 text-sm text-body">{Object.entries(r.by_port_kt).map(([k, v]) => <li key={k} className="flex justify-between"><span>{k}</span><span className="font-medium text-strong">{v}</span></li>)}</ul></div></SpotlightCard>
          </div>
          <SpotlightCard><div className="p-5"><h3 className="text-sm font-semibold text-strong">What each limit costs you</h3><p className="mt-1 text-xs text-muted">Extra saving per month if the limit were one kt looser (shadow price).</p>
            <table className="mt-3 w-full text-left text-xs"><thead className="text-muted"><tr><th className="py-1">Limit</th><th>Used / limit (kt)</th><th>Saving per extra kt</th></tr></thead><tbody>{r.binding_limits.map((b) => <tr key={b.limit} className="border-t border-border-soft"><td className="py-1.5 font-medium text-strong">{b.limit}</td><td>{b.used_kt} / {b.limit_kt}</td><td>₹{b.saving_inr_lakh_per_extra_kt_per_month} lakh</td></tr>)}</tbody></table></div></SpotlightCard>
          <SpotlightCard><div className="max-h-80 overflow-auto p-5"><h3 className="text-sm font-semibold text-strong">The plan</h3>
            <table className="mt-3 w-full text-left text-xs"><thead className="sticky top-0 bg-white text-muted"><tr><th className="py-1">Origin</th><th>Port</th><th>Plant</th><th>kt</th><th>Landed ₹/t</th></tr></thead><tbody>{r.allocation.map((a, i) => <tr key={i} className="border-t border-border-soft"><td className="py-1.5">{a.origin}</td><td>{a.port}</td><td>{a.plant}</td><td className="font-medium text-strong">{a.kt}</td><td>{a.landed_inr_per_t}</td></tr>)}</tbody></table></div></SpotlightCard>
          <Fine>{r.method}</Fine>
        </div>
      )}
    </div>
  );
}

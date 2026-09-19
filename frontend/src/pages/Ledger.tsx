import { useCallback, useEffect, useState } from "react";
import { CheckCircle2, ShieldAlert, Link2 } from "lucide-react";
import SpotlightCard from "../components/SpotlightCard";
import { Field, Note, PageHeader, Stat, btnCls, errText, inputCls } from "../components/ui";
import { api } from "../lib/api";

interface Entry { id: number; fixture_date: string; vessel_name: string; origin_country: string; destination_port: string; cargo_tonnes: number; charter_type: string; rate_usd_per_tonne: number | null; is_sample: boolean; hash: string; prev_hash: string }
interface Chain { valid: boolean; entries: number; head_hash?: string; first_broken_id: number | null; reason: string | null }
interface Bench {
  id: number; date: string; vessel: string; route: string; rate: number | null; is_sample: boolean; illustrative_rate?: number; rate_vs_illustrative_pct?: number; note?: string;
  timing: { index_at_fixture: number; percentile_in_trailing_90d: number; best_bdi_within_30d: number; best_day: string; missed_saving_pct: number; forward_30d_change_pct: number } | null;
}
const ORIGINS = ["Australia", "United States", "Mozambique", "Russia", "Indonesia"];
const PORTS = ["Paradip", "Visakhapatnam", "Gangavaram", "Dhamra", "Gopalpur", "Haldia"];

export default function Ledger() {
  const [entries, setEntries] = useState<Entry[]>([]);
  const [chain, setChain] = useState<Chain | null>(null);
  const [bench, setBench] = useState<{ rows: Bench[]; summary: { fixtures: number; avg_missed_saving_pct: number | null }; method: string } | null>(null);
  const [err, setErr] = useState("");
  const [f, setF] = useState({ fixture_date: new Date().toISOString().slice(0, 10), vessel_name: "", origin_country: "Australia", destination_port: "Paradip", cargo_tonnes: "75000", charter_type: "spot", rate_usd_per_tonne: "", notes: "" });

  const load = useCallback(async () => {
    const l = (await api.get<{ entries: Entry[]; chain: Chain }>("/ledger")).data;
    setEntries(l.entries); setChain(l.chain);
    setBench((await api.get("/ledger/benchmark")).data);
  }, []);
  useEffect(() => { load().catch(() => undefined); }, [load]);

  async function add() {
    setErr("");
    try {
      await api.post("/ledger", { ...f, cargo_tonnes: Number(f.cargo_tonnes), rate_usd_per_tonne: f.rate_usd_per_tonne === "" ? null : Number(f.rate_usd_per_tonne), notes: f.notes || null });
      setF({ ...f, vessel_name: "", rate_usd_per_tonne: "", notes: "" });
      await load();
    } catch (e) { setErr(errText(e)); }
  }
  async function sample() { setErr(""); try { await api.post("/ledger/sample"); await load(); } catch (e) { setErr(errText(e)); } }
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <PageHeader title="Fixture ledger" subtitle="Record charters in a tamper-evident chain, then benchmark each one against the freight market around its date." />

      {chain && (
        <div className={`flex items-center gap-3 rounded-2xl border px-4 py-3 ${chain.valid ? "border-up/30 bg-up/10" : "border-down/40 bg-down/10"}`}>
          {chain.valid ? <CheckCircle2 className="h-5 w-5 text-up" /> : <ShieldAlert className="h-5 w-5 text-down" />}
          <div className="text-sm">
            <p className={`font-semibold ${chain.valid ? "text-up" : "text-down"}`}>{chain.valid ? `Chain verified: ${chain.entries} entries intact` : `Chain broken at entry #${chain.first_broken_id}`}</p>
            <p className="text-xs text-body">{chain.valid ? `Head hash ${chain.head_hash?.slice(0, 16)}…` : chain.reason}</p>
          </div>
        </div>
      )}

      <SpotlightCard>
        <div className="p-6">
          <h2 className="text-sm font-semibold text-strong">Add a fixture</h2>
          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Field label="Fixture date"><input type="date" className={inputCls} value={f.fixture_date} onChange={set("fixture_date")} /></Field>
            <Field label="Vessel"><input className={inputCls} value={f.vessel_name} onChange={set("vessel_name")} placeholder="MV Example" /></Field>
            <Field label="Origin"><select className={inputCls} value={f.origin_country} onChange={set("origin_country")}>{ORIGINS.map((o) => <option key={o}>{o}</option>)}</select></Field>
            <Field label="Discharge port"><select className={inputCls} value={f.destination_port} onChange={set("destination_port")}>{PORTS.map((o) => <option key={o}>{o}</option>)}</select></Field>
            <Field label="Cargo (t)"><input className={inputCls} value={f.cargo_tonnes} onChange={set("cargo_tonnes")} /></Field>
            <Field label="Type"><select className={inputCls} value={f.charter_type} onChange={set("charter_type")}><option value="spot">Spot</option><option value="coa">COA</option><option value="time_charter">Time charter</option></select></Field>
            <Field label="Rate ($/t, optional)"><input className={inputCls} value={f.rate_usd_per_tonne} onChange={set("rate_usd_per_tonne")} /></Field>
            <div className="flex items-end gap-2"><button className={btnCls + " flex-1"} onClick={add} disabled={f.vessel_name.length < 2}>Add to ledger</button></div>
          </div>
          {err && <p className="mt-3 text-xs text-down">{err}</p>}
          <div className="mt-4 flex items-center gap-3">
            <button onClick={sample} className="rounded-lg border border-border-soft px-3 py-1.5 text-xs text-body hover:border-cyan hover:text-cyan">Load 6 illustrative sample entries</button>
            <span className="text-xs text-muted">Samples are invented for demonstration and are marked as such. There is no public source of real fixtures.</span>
          </div>
        </div>
      </SpotlightCard>

      {bench && bench.rows.length > 0 && (
        <SpotlightCard>
          <div className="p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-sm font-semibold text-strong">Benchmark against the market</h2>
              <div className="w-48"><Stat label="Avg missed saving" value={bench.summary.avg_missed_saving_pct === null ? "n/a" : `${bench.summary.avg_missed_saving_pct}%`} tone="warn" /></div>
            </div>
            <div className="mt-4 overflow-x-auto">
              <table className="w-full min-w-[720px] text-left text-sm">
                <thead><tr className="text-xs text-muted"><th className="py-1">Date</th><th>Route</th><th>Index then</th><th>vs 90-day range</th><th>Cheaper day within 30 d</th><th>Missed</th><th>Next 30 d</th><th>Rate check</th></tr></thead>
                <tbody>{bench.rows.map((r) => (
                  <tr key={r.id} className="border-t border-border-soft align-top">
                    <td className="py-1.5 text-strong">{r.date}{r.is_sample && <span className="ml-1 rounded bg-amber/10 px-1 text-[9px] text-amber">sample</span>}</td>
                    <td>{r.route}</td>
                    <td>{r.timing ? r.timing.index_at_fixture.toLocaleString() : "n/a"}</td>
                    <td>{r.timing ? `${r.timing.percentile_in_trailing_90d}th pct` : "n/a"}</td>
                    <td>{r.timing ? `${r.timing.best_day} (${r.timing.best_bdi_within_30d.toLocaleString()})` : "n/a"}</td>
                    <td className={r.timing && r.timing.missed_saving_pct > 10 ? "font-semibold text-down" : ""}>{r.timing ? `${r.timing.missed_saving_pct}%` : "n/a"}</td>
                    <td className={r.timing && r.timing.forward_30d_change_pct > 0 ? "text-down" : "text-up"}>{r.timing ? `${r.timing.forward_30d_change_pct > 0 ? "+" : ""}${r.timing.forward_30d_change_pct}%` : "n/a"}</td>
                    <td>{r.rate_vs_illustrative_pct !== undefined ? `${r.rate_vs_illustrative_pct > 0 ? "+" : ""}${r.rate_vs_illustrative_pct}% vs $${r.illustrative_rate}` : "n/a"}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
            <div className="mt-4"><Note>{bench.method}</Note></div>
          </div>
        </SpotlightCard>
      )}

      <SpotlightCard>
        <div className="p-6">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-strong"><Link2 className="h-4 w-4 text-cyan" /> Ledger entries</h2>
          {entries.length === 0 ? <p className="mt-3 text-sm text-muted">No entries yet.</p> : (
            <ul className="mt-3 divide-y divide-border-soft">
              {entries.map((e) => (
                <li key={e.id} className="py-2.5 text-sm">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-medium text-strong">#{e.id} · {e.vessel_name}{e.is_sample && <span className="ml-2 rounded bg-amber/10 px-1.5 text-[10px] text-amber">sample</span>}</span>
                    <span className="text-xs text-muted">{e.fixture_date} · {e.origin_country} to {e.destination_port} · {e.cargo_tonnes.toLocaleString()} t · {e.charter_type}{e.rate_usd_per_tonne !== null ? ` · $${e.rate_usd_per_tonne}/t` : ""}</span>
                  </div>
                  <p className="mt-0.5 font-mono text-[10px] text-muted">{e.hash.slice(0, 32)}… ← {e.prev_hash.slice(0, 12)}…</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </SpotlightCard>
    </div>
  );
}

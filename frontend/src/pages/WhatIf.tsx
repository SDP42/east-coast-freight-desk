import { useEffect, useMemo, useRef, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis, Cell, ReferenceLine } from "recharts";
import { Flame, RotateCcw, Save, Trash2 } from "lucide-react";
import SpotlightCard from "../components/SpotlightCard";
import LightSelect from "../components/LightSelect";
import { PageHeader, Stat, btnCls, errText, Fine } from "../components/ui";
import { api } from "../lib/api";
import { px } from "../lib/scale";

interface Levers { origin: string; port: string; cargo_tonnes: number; vessel_class: string; freight_shock_pct: number; inr_shock_pct: number; bunker_shock_pct: number; port_delay_days: number; storm_delay_days: number; reroute_nm: number; speed_knots: number; urgency_premium_pct: number }
interface Outcome { total_inr_crore: number; total_usd: number; total_days: number; demurrage_usd: number; freight_usd_per_t: number; notes: string[]; sailing_days: number; port_days: number; lightering_days: number }
interface Run { base: Outcome; scenario: Outcome; delta_pct: number | null; delta_inr_crore: number; delta_days: number; breakdown: { part: string; base: number; scenario: number }[]; note: string }
interface Sens { rows: { lever: string; span: string; low_inr_crore: number; high_inr_crore: number; swing: number }[]; base_inr_crore: number; method: string }
interface Meta { origins: string[]; ports: string[]; vessel_classes: string[]; playbooks: { key: string; title: string; blurb: string; levers: Partial<Levers> }[] }

const DEFAULTS: Levers = { origin: "Australia", port: "Haldia", cargo_tonnes: 75000, vessel_class: "Panamax", freight_shock_pct: 0, inr_shock_pct: 0, bunker_shock_pct: 0, port_delay_days: 0, storm_delay_days: 0, reroute_nm: 0, speed_knots: 12, urgency_premium_pct: 0 };
const SLIDERS: { key: keyof Levers; label: string; min: number; max: number; step: number; unit: string }[] = [
  { key: "freight_shock_pct", label: "Freight rate", min: -40, max: 100, step: 1, unit: "%" },
  { key: "inr_shock_pct", label: "Rupee weaker vs dollar", min: -10, max: 20, step: 0.5, unit: "%" },
  { key: "bunker_shock_pct", label: "Fuel price", min: -40, max: 100, step: 1, unit: "%" },
  { key: "port_delay_days", label: "Port delay", min: 0, max: 15, step: 0.5, unit: " d" },
  { key: "storm_delay_days", label: "Storm delay", min: 0, max: 10, step: 0.5, unit: " d" },
  { key: "reroute_nm", label: "Extra distance (reroute)", min: 0, max: 5000, step: 100, unit: " nm" },
  { key: "speed_knots", label: "Speed", min: 10, max: 15, step: 0.5, unit: " kn" },
  { key: "urgency_premium_pct", label: "Urgency premium", min: 0, max: 30, step: 1, unit: "%" },
];
const PART_COLOR: Record<string, string> = { freight: "#0e7490", "fuel adjustment": "#d97706", "urgency premium": "#7c3aed", lightering: "#059669", demurrage: "#dc2626" };

export default function WhatIf() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [lv, setLv] = useState<Levers>(DEFAULTS);
  const [run, setRun] = useState<Run | null>(null);
  const [sens, setSens] = useState<Sens | null>(null);
  const [err, setErr] = useState("");
  const [saved, setSaved] = useState<{ name: string; lv: Levers; run: Run }[]>([]);
  const [active, setActive] = useState<string | null>(null);
  const tick = useRef(0);

  useEffect(() => { api.get<Meta>("/whatif/meta").then((r) => setMeta(r.data)); }, []);
  useEffect(() => {
    const mine = ++tick.current;
    const t = setTimeout(async () => {
      try {
        const [r, s] = await Promise.all([api.post<Run>("/whatif/run", lv), api.post<Sens>("/whatif/sensitivity", lv)]);
        if (mine === tick.current) { setRun(r.data); setSens(s.data); setErr(""); }
      } catch (e) { if (mine === tick.current) setErr(errText(e)); }
    }, 220);
    return () => clearTimeout(t);
  }, [lv]);

  const set = (patch: Partial<Levers>) => { setActive(null); setLv((p) => ({ ...p, ...patch })); };
  const chart = useMemo(() => (run ? [{ name: "Base", ...Object.fromEntries(run.breakdown.map((b) => [b.part, b.base])) }, { name: "Scenario", ...Object.fromEntries(run.breakdown.map((b) => [b.part, b.scenario])) }] : []), [run]);
  const tornado = useMemo(() => (sens ? sens.rows.map((r) => ({ lever: r.lever, low: r.low_inr_crore, high: r.high_inr_crore, span: r.span })) : []), [sens]);
  const worse = (run?.delta_inr_crore ?? 0) > 0;

  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader title="What-if studio" subtitle="Change freight, rupee, fuel or delays and watch the landed cost move." />

      <div className="mb-4 flex flex-wrap gap-2">
        {meta?.playbooks.map((p) => (
          <button key={p.key} onClick={() => { setActive(p.key); setLv({ ...DEFAULTS, origin: lv.origin, port: lv.port, cargo_tonnes: lv.cargo_tonnes, vessel_class: lv.vessel_class, ...p.levers }); }} title={p.blurb}
            className={`flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs transition ${active === p.key ? "border-cyan bg-cyan/10 text-cyan" : "border-border-soft bg-white text-body hover:border-cyan"}`}>
            <Flame className="h-3.5 w-3.5" /> {p.title}
          </button>
        ))}
        <button onClick={() => { setActive(null); setLv({ ...DEFAULTS, origin: lv.origin, port: lv.port, cargo_tonnes: lv.cargo_tonnes, vessel_class: lv.vessel_class }); }} className="flex items-center gap-1.5 rounded-full border border-border-soft bg-white px-3 py-1.5 text-xs text-muted hover:text-strong"><RotateCcw className="h-3.5 w-3.5" /> Reset</button>
      </div>

      <div className="grid gap-4 lg:grid-cols-5">
        <SpotlightCard className="lg:col-span-2">
          <div className="space-y-4 p-5">
            <div className="grid grid-cols-2 gap-3">
              <LightSelect label="Origin" value={lv.origin} options={meta?.origins ?? [lv.origin]} onChange={(v) => set({ origin: v })} width={170} />
              <LightSelect label="Port" value={lv.port} options={meta?.ports ?? [lv.port]} onChange={(v) => set({ port: v })} width={170} />
              <LightSelect label="Vessel" value={lv.vessel_class} options={meta?.vessel_classes ?? [lv.vessel_class]} onChange={(v) => set({ vessel_class: v })} width={170} />
              <label className="block text-xs font-medium text-body">Cargo: {(lv.cargo_tonnes / 1000).toFixed(0)}k t<input type="range" min={20000} max={200000} step={5000} value={lv.cargo_tonnes} onChange={(e) => set({ cargo_tonnes: Number(e.target.value) })} className="mt-3 w-full accent-cyan" /></label>
            </div>
            <div className="space-y-3 border-t border-border-soft pt-4">
              {SLIDERS.map((s) => (
                <label key={s.key} className="block text-xs font-medium text-body">
                  <span className="flex justify-between"><span>{s.label}</span><b className={Number(lv[s.key]) !== Number(DEFAULTS[s.key]) ? "text-cyan" : "text-muted"}>{Number(lv[s.key]) > 0 && s.unit === "%" ? "+" : ""}{lv[s.key]}{s.unit}</b></span>
                  <input type="range" min={s.min} max={s.max} step={s.step} value={Number(lv[s.key])} onChange={(e) => set({ [s.key]: Number(e.target.value) } as Partial<Levers>)} className="mt-1 w-full accent-cyan" />
                </label>
              ))}
            </div>
          </div>
        </SpotlightCard>

        <div className="space-y-4 lg:col-span-3">
          {err && <p className="text-xs text-down">{err}</p>}
          {run && (
            <>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <Stat label="Base landed cost" value={`₹${run.base.total_inr_crore} cr`} />
                <Stat label="Scenario" value={`₹${run.scenario.total_inr_crore} cr`} tone={worse ? "down" : run.delta_inr_crore < 0 ? "up" : undefined} />
                <Stat label="Change" value={`${(run.delta_pct ?? 0) > 0 ? "+" : ""}${run.delta_pct ?? 0}%`} tone={worse ? "down" : run.delta_inr_crore < 0 ? "up" : undefined} />
                <Stat label="Trip length" value={`${run.scenario.total_days} d (${run.delta_days > 0 ? "+" : ""}${run.delta_days})`} tone={run.delta_days > 3 ? "warn" : undefined} />
              </div>
              <SpotlightCard>
                <div className="p-5">
                  <p className="text-sm font-semibold text-strong">Where the money goes</p>
                  <div className="mt-2 h-56">
                    <ResponsiveContainer>
                      <BarChart data={chart} layout="vertical" margin={{ left: 10 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#dbe4ee" horizontal={false} />
                        <XAxis type="number" tick={{ fontSize: px(11), fill: "#64748b" }} tickFormatter={(v) => `$${(Number(v) / 1e6).toFixed(1)}M`} />
                        <YAxis type="category" dataKey="name" tick={{ fontSize: px(12), fill: "#334e68" }} width={px(64)} />
                        <Tooltip formatter={(v) => `$${Number(v).toLocaleString()}`} /><Legend wrapperStyle={{ fontSize: px(11) }} />
                        {Object.keys(PART_COLOR).map((k) => <Bar key={k} dataKey={k} stackId="a" fill={PART_COLOR[k]} isAnimationActive={false} />)}
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                  {run.scenario.notes.map((n) => <p key={n} className="mt-1 text-[11px] text-muted">{n}</p>)}
                </div>
              </SpotlightCard>
            </>
          )}
          {sens && (
            <SpotlightCard>
              <div className="p-5">
                <p className="text-sm font-semibold text-strong">What matters most for this cargo (tornado)</p>
                <p className="text-xs text-muted">Each lever moved alone across its range; bars show the change in landed cost, ₹ crore.</p>
                <div className="mt-2 h-64">
                  <ResponsiveContainer>
                    <BarChart data={tornado} layout="vertical" margin={{ left: 20 }} stackOffset="sign">
                      <CartesianGrid strokeDasharray="3 3" stroke="#dbe4ee" horizontal={false} />
                      <XAxis type="number" tick={{ fontSize: px(11), fill: "#64748b" }} />
                      <YAxis type="category" dataKey="lever" tick={{ fontSize: px(11), fill: "#334e68" }} width={px(120)} />
                      <Tooltip formatter={(v, n) => [`₹${Number(v).toFixed(2)} cr`, n === "low" ? "Low end" : "High end"]} />
                      <ReferenceLine x={0} stroke="#94a3b8" />
                      <Bar dataKey="low" stackId="s" isAnimationActive={false}>{tornado.map((t) => <Cell key={t.lever} fill={t.low < 0 ? "#059669" : "#d97706"} />)}</Bar>
                      <Bar dataKey="high" stackId="s" isAnimationActive={false}>{tornado.map((t) => <Cell key={t.lever} fill={t.high > 0 ? "#dc2626" : "#059669"} />)}</Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </SpotlightCard>
          )}
        </div>
      </div>

      <SpotlightCard className="mt-4">
        <div className="p-5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm font-semibold text-strong">Scenario comparison</p>
            <button className={btnCls + " flex items-center gap-2"} disabled={!run || saved.length >= 4} onClick={() => run && setSaved((s) => [...s, { name: active ? meta?.playbooks.find((p) => p.key === active)?.title ?? "Scenario" : `Scenario ${s.length + 1}`, lv, run }])}><Save className="h-4 w-4" /> Save this scenario</button>
          </div>
          {saved.length === 0 ? <p className="mt-3 text-sm text-muted">Set the levers, then save up to four scenarios to compare them side by side (for example the base case, a Red Sea closure and a perfect storm).</p> : (
            <div className="mt-3 overflow-x-auto">
              <table className="w-full min-w-[520px] text-left text-sm">
                <thead><tr className="text-xs text-muted"><th className="py-1">Scenario</th><th>Route</th><th>Landed cost</th><th>vs base</th><th>Days</th><th>Demurrage</th><th /></tr></thead>
                <tbody>{saved.map((s, i) => (
                  <tr key={i} className="border-t border-border-soft"><td className="py-1.5 font-medium text-strong">{s.name}</td><td>{s.lv.origin} → {s.lv.port}</td><td>₹{s.run.scenario.total_inr_crore} cr</td>
                    <td className={(s.run.delta_pct ?? 0) > 0 ? "text-down" : "text-up"}>{(s.run.delta_pct ?? 0) > 0 ? "+" : ""}{s.run.delta_pct}%</td><td>{s.run.scenario.total_days}</td><td>${s.run.scenario.demurrage_usd.toLocaleString()}</td>
                    <td><button onClick={() => setSaved((x) => x.filter((_, j) => j !== i))} className="text-muted hover:text-down" aria-label="Remove"><Trash2 className="h-4 w-4" /></button></td></tr>
                ))}</tbody>
              </table>
            </div>
          )}
        </div>
      </SpotlightCard>
      {run && <div className="mt-4"><Fine>{run.note} Freight moves are applied to the route's illustrative rate. Assumed: fuel is 35% of freight, lightering $3.5/t at Sagar for cargo above Haldia's practical ceiling, laytime 2.5 days.</Fine>
      <p className="mt-2 text-xs text-muted">Costs are illustrative estimates, not quotes.</p></div>}
    </div>
  );
}

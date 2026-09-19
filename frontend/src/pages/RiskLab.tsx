import { lazy, Suspense, useEffect, useState } from "react";
import Loading from "../components/Loading";
import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import SpotlightCard from "../components/SpotlightCard";
import { Field, Note, PageHeader, Stat, Tabs, btnCls, errText, inputCls } from "../components/ui";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { px } from "../lib/scale";
import type { FanData } from "../components/three/FanScene";

const FanScene = lazy(() => import("../components/three/FanScene"));
type Tab = "fan" | "car";
interface Fan extends FanData { index_name: string; last_date: string; terminal: { p5: number; p50: number; p95: number }; method: string }
interface Car {
  origin: string; port: string; percentiles_inr_crore: Record<string, number>; mean_inr_crore: number; cost_at_risk_inr_crore: number; base_freight_usd_per_t: number; index_used: string; index_data_through: string;
  histogram: { counts: number[]; edges: number[] }; share_of_variance_pct: Record<string, number>; prob_demurrage: number; expected_demurrage_usd: number; method: string; runs: number;
  assumptions: { laytime_days: number; demurrage_usd_per_day: number };
}

function FanTab() {
  const [idx, setIdx] = useState("BPI");
  const [horizon, setHorizon] = useState(60);
  const [d, setD] = useState<Fan | null>(null);
  const [err, setErr] = useState("");
  useEffect(() => { setD(null); setErr(""); api.get<Fan>(`/lab/fan/${idx}`, { params: { horizon } }).then((r) => setD(r.data)).catch((e) => setErr(errText(e))); }, [idx, horizon]);
  return (
    <SpotlightCard>
      <div className="p-6">
        <div className="flex flex-wrap items-end gap-4">
          <Field label="Index"><select className={inputCls} value={idx} onChange={(e) => setIdx(e.target.value)}>{["BCI", "BPI", "BSI", "BHSI"].map((i) => <option key={i}>{i}</option>)}</select></Field>
          <Field label={`Horizon: ${horizon} days`}><input type="range" min={20} max={120} step={10} value={horizon} onChange={(e) => setHorizon(Number(e.target.value))} className="mt-2 w-48 accent-cyan" /></Field>
          <p className="pb-2 text-xs text-muted">Drag to orbit. Each thread is one possible future.</p>
        </div>
        {err && <p className="mt-3 text-xs text-down">{err}</p>}
        <div className="relative mt-4 h-[30rem] overflow-hidden rounded-2xl border border-border-soft bg-gradient-to-b from-sky-50 to-white">
          {d ? <Suspense fallback={null}><FanScene className="h-full" data={d} /></Suspense> : <div className="flex h-full items-center justify-center"><Loading label="Simulating 400 paths" pattern="rain" grid={4} /></div>}
        </div>
        {d && (
          <div className="mt-4 space-y-3">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Stat label="Last value" value={d.last_value.toLocaleString()} /><Stat label={`In ${d.horizon} days, 5%`} value={d.terminal.p5.toLocaleString()} tone="up" />
              <Stat label="Median" value={d.terminal.p50.toLocaleString()} /><Stat label="95%" value={d.terminal.p95.toLocaleString()} tone="down" />
            </div>
            <Note kind="warn">{d.method} Data through {d.last_date}: the freight indices end in July 2019, so this shows the shape of risk, not a view on today's market.</Note>
          </div>
        )}
      </div>
    </SpotlightCard>
  );
}

function CarTab() {
  const [origin, setOrigin] = useState("Australia");
  const [port, setPort] = useState("Haldia");
  const [cargo, setCargo] = useState("75000");
  const [vc, setVc] = useState("Panamax");
  const [d, setD] = useState<Car | null>(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  async function run() { setBusy(true); setErr(""); try { setD((await api.get<Car>("/lab/cost-at-risk", { params: { origin, port, cargo_tonnes: Number(cargo), vessel_class: vc } })).data); } catch (e) { setErr(errText(e)); } finally { setBusy(false); } }
  useEffect(() => { run(); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const bins = d ? d.histogram.counts.map((c, i) => ({ x: (d.histogram.edges[i] + d.histogram.edges[i + 1]) / 2, c })) : [];
  const p50 = d?.percentiles_inr_crore["50"], p95 = d?.percentiles_inr_crore["95"];
  return (
    <SpotlightCard>
      <div className="p-6">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          <Field label="Origin"><select className={inputCls} value={origin} onChange={(e) => setOrigin(e.target.value)}>{["Australia", "United States", "Mozambique", "Russia", "Indonesia"].map((o) => <option key={o}>{o}</option>)}</select></Field>
          <Field label="Port"><select className={inputCls} value={port} onChange={(e) => setPort(e.target.value)}>{["Paradip", "Visakhapatnam", "Gangavaram", "Dhamra", "Gopalpur", "Haldia"].map((o) => <option key={o}>{o}</option>)}</select></Field>
          <Field label="Cargo (t)"><input className={inputCls} value={cargo} onChange={(e) => setCargo(e.target.value)} /></Field>
          <Field label="Vessel"><select className={inputCls} value={vc} onChange={(e) => setVc(e.target.value)}>{["Capesize", "Panamax", "Supramax", "Handysize"].map((o) => <option key={o}>{o}</option>)}</select></Field>
          <div className="flex items-end"><button className={btnCls + " w-full"} onClick={run} disabled={busy}>{busy ? "Simulating…" : "Simulate 5,000 outcomes"}</button></div>
        </div>
        {err && <p className="mt-3 text-xs text-down">{err}</p>}
        {d && (
          <div className="mt-5 space-y-4">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
              <Stat label="Median landed cost" value={`₹${p50} cr`} /><Stat label="95th percentile" value={`₹${p95} cr`} tone="down" />
              <Stat label="Cost at risk (P95 − P50)" value={`₹${d.cost_at_risk_inr_crore} cr`} tone="warn" /><Stat label="Chance of demurrage" value={`${Math.round(d.prob_demurrage * 100)}%`} /><Stat label="Expected demurrage" value={`$${d.expected_demurrage_usd.toLocaleString()}`} />
            </div>
            <div className="h-64">
              <ResponsiveContainer>
                <BarChart data={bins} barCategoryGap={1}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#dbe4ee" vertical={false} />
                  <XAxis dataKey="x" type="number" domain={["dataMin", "dataMax"]} tick={{ fontSize: px(11), fill: "#64748b" }} tickFormatter={(v) => `₹${Number(v).toFixed(0)}`} />
                  <YAxis hide />
                  <Tooltip formatter={(v) => [String(v), "outcomes"]} labelFormatter={(v) => `≈ ₹${Number(v).toFixed(1)} crore`} />
                  {p50 !== undefined && <ReferenceLine x={p50} stroke="#0e7490" strokeWidth={2} label={{ value: "median", fontSize: px(10), fill: "#0e7490", position: "top" }} />}
                  {p95 !== undefined && <ReferenceLine x={p95} stroke="#dc2626" strokeWidth={2} label={{ value: "P95", fontSize: px(10), fill: "#dc2626", position: "top" }} />}
                  <Bar dataKey="c" isAnimationActive={false} radius={[3, 3, 0, 0]}>{bins.map((b) => <Cell key={b.x} fill={p95 !== undefined && b.x > p95 ? "#dc2626" : "#0e7490"} fillOpacity={0.8} />)}</Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="text-sm text-body">What drives the spread: freight <b>{d.share_of_variance_pct.freight}%</b>, currency <b>{d.share_of_variance_pct.currency}%</b>, demurrage <b>{d.share_of_variance_pct.demurrage}%</b>. Freight dominates, so the timing and contract decisions matter more than port choice.</div>
            <Note kind="warn">{d.method} Index used: {d.index_used}, through {d.index_data_through}.</Note>
          </div>
        )}
      </div>
    </SpotlightCard>
  );
}

export default function RiskLab() {
  const { can } = useAuth();
  const [tab, setTab] = useState<Tab>("fan");
  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader title="Risk lab" subtitle="Two ways to see uncertainty: thousands of possible index paths in 3D, and the range of what one cargo could end up costing." />
      <Tabs<Tab> tabs={[{ key: "fan", label: "3D forecast fan" }, ...(can("financial:read") ? [{ key: "car" as Tab, label: "Cost at risk" }] : [])]} value={tab} onChange={setTab} />
      {tab === "fan" ? <FanTab /> : <CarTab />}
    </div>
  );
}

import { useEffect, useState } from "react";
import { px } from "../lib/scale";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import SpotlightCard from "../components/SpotlightCard";
import { Field, Note, PageHeader, Stat, Tabs, btnCls, errText, inputCls, Fine } from "../components/ui";
import { useAuth } from "../lib/auth";
import { api, estimateDemurrage, getPorts, getVesselClasses, type DemurrageResult, type Port, type VesselClass } from "../lib/api";

type Tab = "carbon" | "hedge" | "modal" | "demurrage";
const inr = (n: number) => `₹${(n / 1e5).toLocaleString(undefined, { maximumFractionDigits: 1 })} lakh`;
const ratingColor: Record<string, string> = { A: "bg-up", B: "bg-up/80", C: "bg-amber", D: "bg-orange-500", E: "bg-down" };

interface Carbon {
  vessel_class: string; laden_days: number; fuel_t: number; co2_t: number; co2_kg_per_tonne_cargo: number; attained_aer: number; required_aer: number; rating: string;
  reduction_pct: number; year: number; speed_sweep: { speed_knots: number; days: number; co2_t: number; aer: number; rating: string }[]; note: string;
  assumptions: { fuel_t_per_day_at_12kn: number; co2_factor: number; representative_dwt: number };
}
function CarbonTool() {
  const [vc, setVc] = useState("Panamax");
  const [nm, setNm] = useState("6000");
  const [speed, setSpeed] = useState("12");
  const [ballast, setBallast] = useState(true);
  const [res, setRes] = useState<Carbon | null>(null);
  const [err, setErr] = useState("");
  async function run() {
    setErr("");
    try { setRes((await api.post<Carbon>("/voyage/carbon", { vessel_class: vc, distance_nm: Number(nm), speed_knots: Number(speed), include_ballast_return: ballast })).data); } catch (e) { setErr(errText(e)); }
  }
  return (
    <SpotlightCard>
      <div className="p-6">
        <h2 className="text-sm font-semibold text-strong">Voyage carbon and CII rating</h2>
        <p className="mt-1 text-xs text-muted">Emissions for a round trip and where it lands on the IMO carbon-intensity scale for bulk carriers. Slowing down is the biggest lever.</p>
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-5">
          <Field label="Vessel class"><select className={inputCls} value={vc} onChange={(e) => setVc(e.target.value)}>{["Capesize", "Panamax", "Supramax", "Handysize"].map((v) => <option key={v}>{v}</option>)}</select></Field>
          <Field label="Laden distance (nm)"><input className={inputCls} value={nm} onChange={(e) => setNm(e.target.value)} /></Field>
          <Field label="Speed (knots)"><input className={inputCls} value={speed} onChange={(e) => setSpeed(e.target.value)} /></Field>
          <Field label="Ballast return"><select className={inputCls} value={ballast ? "y" : "n"} onChange={(e) => setBallast(e.target.value === "y")}><option value="y">Include</option><option value="n">Laden only</option></select></Field>
          <div className="flex items-end"><button className={btnCls + " w-full"} onClick={run}>Estimate</button></div>
        </div>
        {err && <p className="mt-3 text-xs text-down">{err}</p>}
        {res && (
          <div className="mt-5 space-y-4">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
              <div className="rounded-xl border border-border-soft bg-panel-light px-3 py-2.5">
                <p className="text-[10px] font-medium uppercase tracking-wide text-muted">CII rating {res.year}</p>
                <span className={`mt-1 inline-flex h-9 w-9 items-center justify-center rounded-lg text-lg font-bold text-white ${ratingColor[res.rating]}`}>{res.rating}</span>
              </div>
              <Stat label="CO₂ (tonnes)" value={res.co2_t.toLocaleString()} />
              <Stat label="Fuel (tonnes)" value={res.fuel_t.toLocaleString()} />
              <Stat label="CO₂ per tonne cargo" value={`${res.co2_kg_per_tonne_cargo} kg`} />
              <Stat label="Attained / required" value={`${res.attained_aer} / ${res.required_aer}`} />
            </div>
            <div className="h-52">
              <ResponsiveContainer>
                <BarChart data={res.speed_sweep}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#dbe4ee" />
                  <XAxis dataKey="speed_knots" tickFormatter={(v) => `${v} kn`} tick={{ fontSize: px(11), fill: "#64748b" }} />
                  <YAxis tick={{ fontSize: px(11), fill: "#64748b" }} width={px(50)} />
                  <Tooltip formatter={(v, n) => [String(v), n === "co2_t" ? "CO₂ (t)" : String(n)]} labelFormatter={(v) => `${v} knots`} />
                  <Bar isAnimationActive={false} dataKey="co2_t" fill="#0e7490" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="flex flex-wrap gap-2">
              {res.speed_sweep.map((s) => (
                <span key={s.speed_knots} className="rounded-full border border-border-soft bg-white px-3 py-1 text-xs text-body">{s.speed_knots} kn · {s.days} d · rating <b>{s.rating}</b></span>
              ))}
            </div>
            <Fine>{res.note} Assumed here: {res.assumptions.fuel_t_per_day_at_12kn} t/day at 12 kn, CO₂ factor {res.assumptions.co2_factor}, representative {res.assumptions.representative_dwt.toLocaleString()} dwt, required reduction {res.reduction_pct}% for {res.year}.</Fine>
          </div>
        )}
      </div>
    </SpotlightCard>
  );
}

interface Hedge {
  spot_inr_per_usd: number; spot_date: string; horizon_vol_pct: number; empirical_p95_move_pct: number; forward_rate: number; forward_premium_pct: number;
  unhedged: { expected_inr: number; worst_case_95_inr: number }; hedged: { expected_inr: number; worst_case_95_inr: number };
  cost_of_hedge_inr: number; worst_case_saved_inr: number; policy_cap_pct: number; within_policy: boolean; note: string;
}
function HedgeTool() {
  const [usd, setUsd] = useState("5000000");
  const [months, setMonths] = useState("6");
  const [ratio, setRatio] = useState("25");
  const [res, setRes] = useState<Hedge | null>(null);
  const [err, setErr] = useState("");
  async function run() {
    setErr("");
    try { setRes((await api.post<Hedge>("/voyage/hedge", { usd_cost: Number(usd), months: Number(months), hedge_ratio_pct: Number(ratio) })).data); } catch (e) { setErr(errText(e)); }
  }
  return (
    <SpotlightCard>
      <div className="p-6">
        <h2 className="text-sm font-semibold text-strong">INR/USD hedging overlay</h2>
        <p className="mt-1 text-xs text-muted">Freight and coal are paid in dollars. See what a partial forward hedge costs and how much worst-case rupee exposure it removes.</p>
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Field label="Freight bill (USD)"><input className={inputCls} value={usd} onChange={(e) => setUsd(e.target.value)} /></Field>
          <Field label="Horizon (months)"><input className={inputCls} value={months} onChange={(e) => setMonths(e.target.value)} /></Field>
          <Field label="Hedge ratio (%)"><input className={inputCls} value={ratio} onChange={(e) => setRatio(e.target.value)} /></Field>
          <div className="flex items-end"><button className={btnCls + " w-full"} onClick={run}>Compute</button></div>
        </div>
        {err && <p className="mt-3 text-xs text-down">{err}</p>}
        {res && (
          <div className="mt-5 space-y-4">
            {!res.within_policy && <Note kind="warn">A {ratio}% hedge is above the {res.policy_cap_pct}% that SAIL's FY25 annual report says is permitted.</Note>}
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Stat label={`Spot (${res.spot_date})`} value={`₹${res.spot_inr_per_usd}`} />
              <Stat label="Forward rate" value={`₹${res.forward_rate}`} />
              <Stat label="Horizon volatility" value={`${res.horizon_vol_pct}%`} />
              <Stat label="Worst 5% move (history)" value={`+${res.empirical_p95_move_pct}%`} tone="warn" />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-xl border border-border-soft p-4"><p className="text-xs font-semibold text-muted">UNHEDGED</p><p className="mt-1 text-sm text-body">Expected {inr(res.unhedged.expected_inr)}</p><p className="text-sm text-down">95% worst case {inr(res.unhedged.worst_case_95_inr)}</p></div>
              <div className="rounded-xl border border-cyan/40 bg-cyan/5 p-4"><p className="text-xs font-semibold text-cyan">HEDGED ({ratio}%)</p><p className="mt-1 text-sm text-body">Expected {inr(res.hedged.expected_inr)}</p><p className="text-sm text-amber">95% worst case {inr(res.hedged.worst_case_95_inr)}</p></div>
            </div>
            <p className="text-sm text-body">Hedging costs about <b>{inr(res.cost_of_hedge_inr)}</b> in expected terms and removes about <b className="text-up">{inr(res.worst_case_saved_inr)}</b> from the 95% worst case.</p>
            <Fine>{res.note}</Fine>
          </div>
        )}
      </div>
    </SpotlightCard>
  );
}

interface Modal {
  plant: string; inr_per_usd: number; note: string;
  options: { port: string; sea_usd_per_t: number; handling_usd_per_t: number; rail_km: number; rail_usd_per_t: number; total_usd_per_t: number; premium_vs_best_pct: number }[];
}
function ModalTool() {
  const [meta, setMeta] = useState<{ plants: string[]; origins: string[] } | null>(null);
  const [plant, setPlant] = useState("Bhilai");
  const [origin, setOrigin] = useState("Australia");
  const [tariff, setTariff] = useState("1.4");
  const [res, setRes] = useState<Modal | null>(null);
  const [err, setErr] = useState("");
  useEffect(() => { api.get("/voyage/plants").then((r) => setMeta(r.data)); }, []);
  async function run() {
    setErr("");
    try { setRes((await api.get<Modal>("/voyage/modal", { params: { plant, origin_country: origin, rail_inr_per_tkm: Number(tariff) } })).data); } catch (e) { setErr(errText(e)); }
  }
  return (
    <SpotlightCard>
      <div className="p-6">
        <h2 className="text-sm font-semibold text-strong">Rail-sea-rail: which port lands coal cheapest at the plant?</h2>
        <p className="mt-1 text-xs text-muted">Sea freight to a discharge port, port handling, then rail to the steel plant. A nearer port is not always cheaper once the rail leg is counted.</p>
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Field label="Steel plant"><select className={inputCls} value={plant} onChange={(e) => setPlant(e.target.value)}>{(meta?.plants ?? [plant]).map((p) => <option key={p}>{p}</option>)}</select></Field>
          <Field label="Origin"><select className={inputCls} value={origin} onChange={(e) => setOrigin(e.target.value)}>{(meta?.origins ?? [origin]).map((p) => <option key={p}>{p}</option>)}</select></Field>
          <Field label="Rail tariff (₹/t-km)"><input className={inputCls} value={tariff} onChange={(e) => setTariff(e.target.value)} /></Field>
          <div className="flex items-end"><button className={btnCls + " w-full"} onClick={run}>Compare ports</button></div>
        </div>
        {err && <p className="mt-3 text-xs text-down">{err}</p>}
        {res && (
          <div className="mt-5 space-y-4">
            <div className="h-56">
              <ResponsiveContainer>
                <BarChart data={res.options} layout="vertical" margin={{ left: 30 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#dbe4ee" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: px(11), fill: "#64748b" }} unit="$" />
                  <YAxis type="category" dataKey="port" tick={{ fontSize: px(11), fill: "#334e68" }} width={px(110)} />
                  <Tooltip />
                  <Bar isAnimationActive={false} dataKey="sea_usd_per_t" stackId="a" fill="#0e7490" name="Sea" />
                  <Bar isAnimationActive={false} dataKey="handling_usd_per_t" stackId="a" fill="#94a3b8" name="Handling" />
                  <Bar isAnimationActive={false} dataKey="rail_usd_per_t" stackId="a" fill="#d97706" name="Rail" radius={[0, 6, 6, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <table className="w-full text-left text-sm">
              <thead><tr className="text-xs text-muted"><th className="py-1">Port</th><th>Sea</th><th>Rail</th><th>Total $/t</th><th>vs best</th></tr></thead>
              <tbody>{res.options.map((o, i) => (
                <tr key={o.port} className="border-t border-border-soft"><td className="py-1.5 font-medium text-strong">{o.port}{i === 0 && <span className="ml-2 rounded-full bg-up/10 px-2 py-0.5 text-[10px] text-up">cheapest</span>}</td><td>${o.sea_usd_per_t}</td><td>${o.rail_usd_per_t} ({o.rail_km} km)</td><td className="font-semibold">${o.total_usd_per_t}</td><td className="text-muted">+{o.premium_vs_best_pct}%</td></tr>
              ))}</tbody>
            </table>
            <Fine>{res.note}</Fine>
          </div>
        )}
      </div>
    </SpotlightCard>
  );
}

function DemurrageTool() {
  const [ports, setPorts] = useState<Port[]>([]);
  const [classes, setClasses] = useState<VesselClass[]>([]);
  const [portId, setPortId] = useState(0);
  const [classId, setClassId] = useState(0);
  const [laytime, setLaytime] = useState("2");
  const [res, setRes] = useState<DemurrageResult | null>(null);
  const [ballast, setBallast] = useState<{ origin_country: string; destination_port_name: string; estimated_ballast_days: number; laycan_wait_days: number; total_idle_days: number }[]>([]);
  useEffect(() => {
    Promise.all([getPorts(), getVesselClasses()]).then(([p, c]) => {
      const dest = p.filter((x) => x.is_destination);
      setPorts(dest); setClasses(c); setPortId(dest[0]?.id ?? 0); setClassId(c.find((x) => x.name === "Panamax")?.id ?? c[0]?.id ?? 0);
    });
  }, []);
  async function run() {
    setRes(await estimateDemurrage(portId, classId, Number(laytime)));
    const cands = ["Australia", "United States", "Mozambique", "Russia", "Indonesia"].map((o) => ({ origin_country: o, destination_port_id: portId, laycan_start: new Date(Date.now() + 10 * 864e5).toISOString().slice(0, 10) }));
    setBallast((await api.post("/financial/ballast-options", cands)).data);
  }
  return (
    <SpotlightCard>
      <div className="p-6">
        <h2 className="text-sm font-semibold text-strong">Demurrage exposure and idle time</h2>
        <p className="mt-1 text-xs text-muted">Expected demurrage from the port's real average turnaround against your laytime, and which origin keeps the ship idle for the fewest days.</p>
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Field label="Port"><select className={inputCls} value={portId} onChange={(e) => setPortId(Number(e.target.value))}>{ports.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</select></Field>
          <Field label="Vessel class"><select className={inputCls} value={classId} onChange={(e) => setClassId(Number(e.target.value))}>{classes.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></Field>
          <Field label="Laytime allowed (days)"><input className={inputCls} value={laytime} onChange={(e) => setLaytime(e.target.value)} /></Field>
          <div className="flex items-end"><button className={btnCls + " w-full"} onClick={run}>Estimate</button></div>
        </div>
        {res && (
          <div className="mt-5 space-y-4">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Stat label="Avg turnaround" value={`${res.actual_turnaround_days} d`} />
              <Stat label="Demurrage days" value={res.demurrage_days} tone={res.demurrage_days > 0 ? "down" : "up"} />
              <Stat label="Rate" value={`$${res.demurrage_rate_usd_per_day.toLocaleString()}/d`} />
              <Stat label="Expected exposure" value={`$${res.expected_demurrage_usd.toLocaleString()}`} tone={res.expected_demurrage_usd > 0 ? "down" : "up"} />
            </div>
            {res.notes.map((n) => <Note key={n}>{n}</Note>)}
            {ballast.length > 0 && (
              <table className="w-full text-left text-sm">
                <thead><tr className="text-xs text-muted"><th className="py-1">Origin</th><th>Ballast days</th><th>Laycan wait</th><th>Total idle</th></tr></thead>
                <tbody>{ballast.map((b, i) => <tr key={b.origin_country} className="border-t border-border-soft"><td className="py-1.5 font-medium text-strong">{b.origin_country}{i === 0 && <span className="ml-2 rounded-full bg-up/10 px-2 py-0.5 text-[10px] text-up">least idle</span>}</td><td>{b.estimated_ballast_days}</td><td>{b.laycan_wait_days}</td><td className="font-semibold">{b.total_idle_days} d</td></tr>)}</tbody>
              </table>
            )}
          </div>
        )}
      </div>
    </SpotlightCard>
  );
}

export default function Voyage() {
  const { can } = useAuth();
  const [tab, setTab] = useState<Tab>("carbon");
  const tabs: { key: Tab; label: string }[] = [{ key: "carbon", label: "Carbon (CII)" }, ...(can("treasury:read") ? [{ key: "hedge" as Tab, label: "INR/USD hedge" }] : []), { key: "modal", label: "Rail-sea-rail" }, ...(can("financial:read") ? [{ key: "demurrage" as Tab, label: "Demurrage & idle time" }] : [])];
  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader title="Voyage economics" subtitle="Carbon, currency, inland logistics and demurrage around the freight rate." />
      <Tabs<Tab> tabs={tabs} value={tab} onChange={setTab} />
      {tab === "carbon" && <CarbonTool />}
      {tab === "hedge" && <HedgeTool />}
      {tab === "modal" && <ModalTool />}
      {tab === "demurrage" && <DemurrageTool />}
    </div>
  );
}
